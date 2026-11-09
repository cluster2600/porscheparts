// Subdivide long edges with exact midpoints and retain each source triangle ID.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/Euler_operations.h>
#include <set>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/version.h>
#include <CGAL/version_macros.h>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

using K = CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;
int main(int argc, char** argv) {
  try {
    static_assert(std::endian::native == std::endian::little);
    if(argc != 4) throw std::runtime_error("input_output_prefix_max_edge_required");
    const double h = std::stod(argv[3]);
    if(!std::isfinite(h) || h <= 0) throw std::runtime_error("positive_edge_limit_required");
    for(auto suffix: {".bin", ".parents", ".exact", ".intervals"})
      if(std::filesystem::exists(std::string(argv[2]) + suffix)) throw std::runtime_error("output_exists");
    std::ifstream in(argv[1], std::ios::binary);
    auto read = [&](auto& x) { if(!in.read(reinterpret_cast<char*>(&x), sizeof(x))) throw std::runtime_error("truncated_input"); };
    std::array<char,8> magic; read(magic);
    if(magic != std::array<char,8>{'M','6','4','T','R','I','1','\0'}) throw std::runtime_error("wrong_format");
    std::uint64_t nv,nf; read(nv); read(nf);
    if(!nv || !nf || nv > 2000000 || nf > 2000000) throw std::runtime_error("input_count_limit");
    Mesh mesh;
    for(std::uint64_t i=0; i<nv; ++i) {
      std::array<double,3> p; read(p);
      for(auto x:p) if(!std::isfinite(x)) throw std::runtime_error("nonfinite_input");
      mesh.add_vertex(K::Point_3(p[0],p[1],p[2]));
    }
    auto parent = mesh.add_property_map<Mesh::Face_index,std::uint64_t>("f:source", UINT64_MAX).first;
    for(std::uint64_t i=0; i<nf; ++i) {
      std::array<std::uint64_t,3> f; read(f);
      for(auto v:f) if(v>=nv) throw std::runtime_error("unknown_vertex");
      auto face = mesh.add_face(Mesh::Vertex_index(f[0]),Mesh::Vertex_index(f[1]),Mesh::Vertex_index(f[2]));
      if(face == Mesh::null_face()) throw std::runtime_error("invalid_face_topology");
      parent[face] = i;
    }
    if(in.peek()!=std::char_traits<char>::eof()) throw std::runtime_error("trailing_input");
    if(!mesh.is_valid() || !CGAL::is_closed(mesh)) throw std::runtime_error("closed_valid_input_required");
    const K::FT limit = K::FT(h)*K::FT(h);
    std::set<std::pair<K::FT,Mesh::Edge_index>> pending;
    auto length = [&](Mesh::Edge_index e) {
      auto he=mesh.halfedge(e);
      return CGAL::squared_distance(mesh.point(mesh.source(he)),mesh.point(mesh.target(he)));
    };
    auto queue = [&](Mesh::Edge_index e) {
      auto squared=length(e);
      if(squared>limit) pending.emplace(squared,e);
    };
    for(auto e:mesh.edges()) queue(e);
    unsigned splits=0;
    while(!pending.empty()) {
      auto item=*pending.rbegin(); pending.erase(item);
      auto e=item.second;
      if(length(e)!=item.first) continue;
      if(mesh.number_of_vertices()+1>1000000 || mesh.number_of_faces()+2>2000000)
        throw std::runtime_error("output_count_limit");
      auto he=mesh.halfedge(e);
      const auto midpoint=CGAL::midpoint(mesh.point(mesh.source(he)),mesh.point(mesh.target(he)));
      auto added=CGAL::Euler::split_edge(he,mesh);
      mesh.point(mesh.target(added))=midpoint;
      auto opposite=mesh.opposite(added);
      auto left=parent[mesh.face(added)], right=parent[mesh.face(opposite)];
      auto diagonal=CGAL::Euler::split_face(added,mesh.next(mesh.next(added)),mesh);
      parent[mesh.face(diagonal)]=left; parent[mesh.face(mesh.opposite(diagonal))]=left;
      auto other=CGAL::Euler::split_face(mesh.prev(opposite),mesh.next(opposite),mesh);
      parent[mesh.face(other)]=right; parent[mesh.face(mesh.opposite(other))]=right;
      for(auto edge:{e,mesh.edge(added),mesh.edge(diagonal),mesh.edge(other)}) queue(edge);
      ++splits;
    }
    for(auto e:mesh.edges()) if(length(e)>limit) throw std::runtime_error("long_edge_remaining");
    if(!mesh.is_valid() || !CGAL::is_closed(mesh) || !CGAL::is_triangle_mesh(mesh)) throw std::runtime_error("invalid_output_topology");
    std::ofstream out(std::string(argv[2])+".bin",std::ios::binary), parents(std::string(argv[2])+".parents",std::ios::binary), exact(std::string(argv[2])+".exact"), intervals(std::string(argv[2])+".intervals",std::ios::binary);
    auto write = [&](auto& stream, const auto& x) {stream.write(reinterpret_cast<const char*>(&x),sizeof(x));};
    std::uint64_t new_nv=mesh.number_of_vertices(),new_nf=mesh.number_of_faces();
    write(out,magic);write(out,new_nv);write(out,new_nf);exact<<new_nv<<'\n';
    std::uint64_t index=0;
    for(auto v:mesh.vertices()) {
      if(v.idx()!=index++) throw std::runtime_error("unexpected_vertex_indices");
      auto p=mesh.point(v);
      for(auto x:{p.x(),p.y(),p.z()}) {
        double d=CGAL::to_double(x); auto bounds=CGAL::to_interval(x);
        if(!std::isfinite(d) || d<bounds.first || d>bounds.second) throw std::runtime_error("invalid_rounding_bounds");
        write(out,d);write(intervals,bounds.first);write(intervals,bounds.second);
        exact<<CGAL::exact(x)<<' ';
      }
      exact<<'\n';
    }
    for(auto f:mesh.faces()) {
      if(parent[f]>=nf) throw std::runtime_error("missing_source_face");
      auto he=mesh.halfedge(f);
      std::array<std::uint64_t,3> ids{mesh.source(he).idx(),mesh.target(he).idx(),mesh.target(mesh.next(he)).idx()};
      write(out,ids);write(parents,parent[f]);
    }
    out.flush();parents.flush();exact.flush();intervals.flush();
    if(!out || !parents || !exact || !intervals) throw std::runtime_error("output_failure");
    std::cout<<"{\"CGAL\":\""<<CGAL_VERSION_STR<<"\",\"vertices\":"<<new_nv<<",\"triangles\":"<<new_nf<<",\"splits\":"<<splits<<"}\n";
  } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
