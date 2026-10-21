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
struct Original_projection {
  const Tree* tree;Mesh* candidate;
  Point operator()(Vertex v)const{return tree->closest_point(candidate->point(v));}
};
int main(int argc,char** argv) {
  try {
    if(argc!=3)throw std::runtime_error("Usage: quality-patch original.bin fresh-output-directory");
    fs::path output=argv[2];
    if(!fs::create_directory(output))throw std::runtime_error("Output directory must be new");
    auto start=std::chrono::steady_clock::now();
    const Mesh original=read_surface(argv[1]);Mesh candidate=original;
    const Quality before=quality(original);
    std::vector<bool> seeds(original.num_vertices(),false),in_patch(original.num_faces(),false),
      patch_vertex(original.num_vertices(),false);
    std::size_t bad_seeds=0,seed_count=0,patch_count=0;
    for(auto f:original.faces())if(triangle_quality(original,f)<2.0/29.0) {
      ++bad_seeds;for(auto v:vertices(original,f))seeds[v.idx()]=true;
    }
    for(bool v:seeds)seed_count+=v;
    std::vector<Face> patch;
    for(auto f:original.faces()) {
      auto v=vertices(original,f);bool inside=seeds[v[0].idx()]||seeds[v[1].idx()]||seeds[v[2].idx()];
      in_patch[f.idx()]=inside;
      if(inside) { patch.push_back(f);++patch_count;for(auto id:v)patch_vertex[id.idx()]=true; }
    }
    auto fixed=candidate.add_property_map<Vertex,bool>("v:quality-fixed",false).first;
    for(auto f:original.faces())if(!in_patch[f.idx()])for(auto v:vertices(original,f))fixed[v]=true;
    std::size_t patch_vertices=0,exterior_fixed=0,clip_fixed=0;
    for(auto v:original.vertices()) {
      if(patch_vertex[v.idx()]) { ++patch_vertices;exterior_fixed+=fixed[v]; }
      if(original.point(v).x()==-76.0||original.point(v).x()==76.0) {
        if(patch_vertex[v.idx()])++clip_fixed;fixed[v]=true;
      }
    }
    auto constrained=candidate.add_property_map<Mesh::Edge_index,bool>("e:quality-fixed",false).first;
    for(auto e:candidate.edges()) {
      auto h=candidate.halfedge(e);constrained[e]=fixed[candidate.source(h)]&&fixed[candidate.target(h)];
    }
    Tree tree(faces(original).first,faces(original).second,original);tree.build();
    if(!patch.empty())PMP::isotropic_remeshing(patch,0.0,candidate,
      CGAL::parameters::number_of_iterations(1).number_of_relaxation_steps(1)
      .do_split(false).do_collapse(false).do_flip(true).do_project(true)
      .relax_constraints(false).protect_constraints(false)
      .vertex_is_constrained_map(fixed).edge_is_constrained_map(constrained)
      .projection_functor(Original_projection{&tree,&candidate}));
    const Quality after=quality(candidate);
    bool fixed_same=true,outside_same=true;
    for(auto v:original.vertices())if(fixed[v]&&candidate.point(v)!=original.point(v))fixed_same=false;
    for(auto f:original.faces())if(!in_patch[f.idx()]
      &&canonical_face(original,f)!=canonical_face(candidate,f))outside_same=false;
    bool valid=CGAL::is_closed(candidate)&&CGAL::is_triangle_mesh(candidate)&&CGAL::is_valid_polygon_mesh(candidate);
    bool count_same=original.number_of_vertices()==candidate.number_of_vertices()
      &&original.number_of_faces()==candidate.number_of_faces();
    bool improve=after.bad<before.bad&&after.minimum>=before.minimum;
    bool proposed=improve&&valid&&fixed_same&&outside_same&&count_same;
    write_surface(candidate,output/"proposed-surface.bin");
    if(proposed)write_surface(candidate,output/"quality-candidate.bin");
    auto boolean=[](bool value){return value?"true":"false";};
    std::ostringstream report;
    report<<std::setprecision(17)<<"{\"schema\":\"962-original-local-quality-pass/v1\",\"status\":\""
      <<(proposed?"quality_improvement_candidate_all_independent_gates_pending":"quality_pass_rejected_original_preserved")
      <<"\",\"CGAL\":\""<<CGAL_VERSION_STR<<"\",\"full_surface_before\":"<<json_quality(before)
      <<",\"full_surface_after\":"<<json_quality(after)<<",\"bad_seed_faces\":"<<bad_seeds
      <<",\"seed_vertices\":"<<seed_count<<",\"patch_faces\":"<<patch_count<<",\"patch_vertices\":"<<patch_vertices
      <<",\"patch_exterior_fixed_vertices\":"<<exterior_fixed<<",\"patch_clip_plane_vertices\":"<<clip_fixed
      <<",\"fixed_source_vertices_unchanged\":"<<boolean(fixed_same)<<",\"outside_source_faces_unchanged\":"<<boolean(outside_same)
      <<",\"vertex_and_face_counts_unchanged\":"<<boolean(count_same)<<",\"closed_valid_triangle_mesh\":"<<boolean(valid)
      <<",\"quality_objective_improved\":"<<boolean(improve)<<",\"quality_candidate_written\":"<<boolean(proposed)
      <<",\"source_master_altered\":false,\"complete_semantic_constraint_map\":false,\"engineering_accepted\":false"
      <<",\"controls\":{\"target_edge_length_mm\":0,\"do_split\":false,\"do_collapse\":false,\"do_flip\":true,\"do_project\":true,\"relax_constraints\":false,\"protect_constraints\":false,\"atomic_iterations\":1,\"relaxation_steps\":1,\"projection_reference\":\"immutable_original_surface\"}"
      <<",\"wall_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}";
    std::ofstream stream(output/"report.json");stream<<report.str()<<"\n";stream.close();
    if(!stream)throw std::runtime_error("Report output failed");
    std::cout<<report.str()<<std::endl;return proposed?0:3;
  }catch(const std::exception& error){std::cerr<<"quality-patch failure: "<<error.what()<<std::endl;return 2;}
}
