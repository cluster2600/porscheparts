// Exact retained source slices; see source-reuse.json. No legacy main.
#pragma once
#include <algorithm>
// Separate analysis candidate only: original-source local quality remeshing.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/remesh.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_face_graph_triangle_primitive.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

using Kernel=CGAL::Exact_predicates_inexact_constructions_kernel;
using Point=Kernel::Point_3;
using Mesh=CGAL::Surface_mesh<Point>;
using Vertex=Mesh::Vertex_index;
using Face=Mesh::Face_index;
using Primitive=CGAL::AABB_face_graph_triangle_primitive<Mesh>;
using Tree=CGAL::AABB_tree<CGAL::AABB_traits<Kernel,Primitive>>;
namespace PMP=CGAL::Polygon_mesh_processing;
namespace fs=std::filesystem;

template<class T> T read_value(std::istream& input) {
  T value;
  if(!input.read(reinterpret_cast<char*>(&value),sizeof(value)))
    throw std::runtime_error("Incomplete indexed surface");
  return value;
}
template<class T> void write_value(std::ostream& out,T value) {
  out.write(reinterpret_cast<const char*>(&value),sizeof(value));
}
std::array<Vertex,3> vertices(const Mesh& mesh,Face face) {
  auto h=mesh.halfedge(face);
  return {mesh.source(h),mesh.target(h),mesh.target(mesh.next(h))};
}
std::array<std::size_t,3> canonical_face(const Mesh& mesh,Face face) {
  auto v=vertices(mesh,face);
  std::array<std::size_t,3> best={v[0].idx(),v[1].idx(),v[2].idx()};
  for(int i=1;i<3;++i) {
    std::array<std::size_t,3> row={v[i].idx(),v[(i+1)%3].idx(),v[(i+2)%3].idx()};
    if(row<best)best=row;
  }
  return best;
}
Mesh read_surface(const fs::path& path) {
  std::ifstream in(path,std::ios::binary);char magic[8];
  if(!in.read(magic,8)||std::memcmp(magic,"962SURF1",8))
    throw std::runtime_error("Expected binary64/uint64 indexed surface");
  auto nv=read_value<std::uint64_t>(in),nf=read_value<std::uint64_t>(in);
  if(!nv||!nf||nv>2000000||nf>2000000||fs::file_size(path)!=24+24*(nv+nf))
    throw std::runtime_error("Invalid indexed surface counts");
  Mesh mesh;mesh.reserve(nv,3*nf/2,nf);std::vector<Vertex> ids;ids.reserve(nv);
  for(std::uint64_t i=0;i<nv;++i) {
    double x=read_value<double>(in),y=read_value<double>(in),z=read_value<double>(in);
    if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))
      throw std::runtime_error("Nonfinite source point");
    ids.push_back(mesh.add_vertex(Point(x,y,z)));
  }
  for(std::uint64_t i=0;i<nf;++i) {
    auto a=read_value<std::uint64_t>(in),b=read_value<std::uint64_t>(in),c=read_value<std::uint64_t>(in);
    if(a>=nv||b>=nv||c>=nv||a==b||b==c||c==a
       ||CGAL::collinear(mesh.point(ids[a]),mesh.point(ids[b]),mesh.point(ids[c]))
       ||mesh.add_face(ids[a],ids[b],ids[c])==Mesh::null_face())
      throw std::runtime_error("Invalid source triangle");
  }
  if(!CGAL::is_closed(mesh)||!CGAL::is_triangle_mesh(mesh)||!CGAL::is_valid_polygon_mesh(mesh))
    throw std::runtime_error("Closed valid oriented triangular source required");
  return mesh;
}
void write_surface(const Mesh& mesh,const fs::path& path) {
  if(fs::exists(path)||fs::is_symlink(path))throw std::runtime_error("Existing output preserved");
  std::ofstream out(path,std::ios::binary);out.write("962SURF1",8);
  write_value<std::uint64_t>(out,mesh.number_of_vertices());
  write_value<std::uint64_t>(out,mesh.number_of_faces());
  std::vector<std::uint64_t> ids(mesh.num_vertices(),std::uint64_t(-1));
  std::uint64_t i=0;
  for(auto v:mesh.vertices()) {
    ids[v.idx()]=i++;auto p=mesh.point(v);
    write_value<double>(out,p.x());write_value<double>(out,p.y());write_value<double>(out,p.z());
  }
  for(auto f:mesh.faces())for(auto v:vertices(mesh,f))write_value<std::uint64_t>(out,ids[v.idx()]);
  out.close();if(!out)throw std::runtime_error("Surface output failed");
}
double triangle_quality(const Mesh& mesh,Face f) {
  auto v=vertices(mesh,f);auto u=mesh.point(v[1])-mesh.point(v[0]);auto w=mesh.point(v[2])-mesh.point(v[0]);
  double sum=u.squared_length()+w.squared_length()+(w-u).squared_length();
  return 2*std::sqrt(3.0)*std::sqrt(CGAL::cross_product(u,w).squared_length())/sum;
}
struct Quality { std::size_t faces=0,bad=0;double minimum=1; };
Quality quality(const Mesh& mesh) {
  Quality result;
  for(auto f:mesh.faces()) {
    double q=triangle_quality(mesh,f);
    if(!std::isfinite(q)||q<0)throw std::runtime_error("Nonfinite triangle quality");
    ++result.faces;result.bad+=q<2.0/29.0;result.minimum=std::min(result.minimum,q);
  }
  return result;
}
std::string json_quality(const Quality& q) {
  std::ostringstream s;s<<std::setprecision(17)<<"{\"triangles\":"<<q.faces
    <<",\"below_necessary_bound\":"<<q.bad<<",\"minimum_triangle_SICN\":"<<q.minimum<<"}";
  return s.str();
}
// Same scalar policy/operation order as CGAL5.6 Edge_collapse.h shared-triangle
// predicate and constructor: strict squared-area ratio1e8, then cos(1degree)^2.
int ordinary(const Point& p0,const Point& p1,const Point& p2,const Point& p3) {
  Kernel traits;auto e01=traits.construct_vector_3_object()(p0,p1),e02=traits.construct_vector_3_object()(p0,p2),e03=traits.construct_vector_3_object()(p0,p3);
  auto n012=traits.construct_cross_product_vector_3_object()(e01,e02),n023=traits.construct_cross_product_vector_3_object()(e02,e03);
  auto l012=traits.compute_scalar_product_3_object()(n012,n012),l023=traits.compute_scalar_product_3_object()(n023,n023);
  auto larger=(std::max)(l012,l023),smaller=(std::min)(l012,l023);
  if(!(larger<1e8*smaller))return 1;
  auto dot=traits.compute_scalar_product_3_object()(n012,n023);if(CGAL_NTS is_positive(dot))return 0;
  const double max_cos_squared=CGAL::square(std::cos(1.0*CGAL_PI/180.0));
  return dot*dot<=max_cos_squared*(l012*l023)?0:2;
}
