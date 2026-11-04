#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/detect_features.h>
#include <CGAL/Polygon_mesh_processing/remesh.h>
#include <CGAL/Polygon_mesh_processing/shape_predicates.h>
#include <sys/resource.h>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <queue>
#include <set>
#include <vector>

using K = CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;
namespace PMP = CGAL::Polygon_mesh_processing;

// PMPSizingField implementation. Original sizes follow graph distance to locks;
// sizes of split vertices interpolate the two edge endpoints at registration.
struct Locked_distance_sizing {
  using FT = double;
  using Point_3 = K::Point_3;
  Mesh::Property_map<Mesh::Vertex_index, double> sizes;
  FT at(Mesh::Vertex_index v, const Mesh&) const { return sizes[v]; }
  std::optional<FT> is_too_long(Mesh::Vertex_index a, Mesh::Vertex_index b, const Mesh& m) const {
    double length = CGAL::to_double(CGAL::squared_distance(m.point(a),m.point(b)));
    double threshold = std::pow(4./3. * std::min(sizes[a],sizes[b]),2);
    return length > threshold ? std::optional<FT>(length/threshold) : std::nullopt;
  }
  std::optional<FT> is_too_short(Mesh::Halfedge_index h, const Mesh& m) const {
    auto a=m.source(h), b=m.target(h);
    double length = CGAL::to_double(CGAL::squared_distance(m.point(a),m.point(b)));
    double threshold = std::pow(.8 * std::min(sizes[a],sizes[b]),2);
    return length < threshold ? std::optional<FT>(length/threshold) : std::nullopt;
  }
  Point_3 split_placement(Mesh::Halfedge_index h, const Mesh& m) const {
    return CGAL::midpoint(m.point(m.source(h)),m.point(m.target(h)));
  }
  void register_split_vertex(Mesh::Vertex_index v, const Mesh& m) {
    double total=0; unsigned count=0;
    for(auto h:CGAL::halfedges_around_target(v,m)) { total+=sizes[m.source(h)]; ++count; }
    if(count!=2) throw std::runtime_error("Unexpected split registration topology");
    sizes[v]=total/count;
  }
};

int main(int argc,char** argv) {
  try {
    if(argc!=5 && argc!=6) return 2;
    bool preflight=argc==6 && std::string(argv[5])=="--preflight-only";
    if(argc==6 && !preflight) return 2;
    if(std::ifstream(argv[3]).good() || std::ifstream(argv[4]).good()) return 3;
    const auto started=std::chrono::steady_clock::now();
    Mesh mesh;
    if(!CGAL::IO::read_polygon_mesh(argv[1],mesh) || !CGAL::is_triangle_mesh(mesh)) return 4;
    std::vector<Mesh::Face_index> degenerate;
    PMP::degenerate_faces(mesh,std::back_inserter(degenerate));
    if(!degenerate.empty()) return 4;
    std::ifstream input_mask(argv[2]); if(!input_mask) return 4;
    std::set<std::size_t> protected_faces; std::size_t index;
    while(input_mask>>index) if(index>=mesh.number_of_faces() || !protected_faces.insert(index).second) return 4;
    if(!input_mask.eof() || protected_faces.empty()) return 4;
    auto ec=mesh.add_property_map<Mesh::Edge_index,bool>("e:locked",false).first;
    auto vc=mesh.add_property_map<Mesh::Vertex_index,bool>("v:locked",false).first;
    auto size=mesh.add_property_map<Mesh::Vertex_index,double>("v:size",.2).first;
    auto distance=mesh.add_property_map<Mesh::Vertex_index,double>("v:distance",std::numeric_limits<double>::infinity()).first;
    PMP::detect_sharp_edges(mesh,30.,ec);
    std::vector<Mesh::Face_index> selected;
    for(auto face:mesh.faces()) {
      if(protected_faces.count(face.idx())) {
        for(auto h:CGAL::halfedges_around_face(mesh.halfedge(face),mesh)) ec[mesh.edge(h)]=true;
      } else selected.push_back(face);
    }
    std::size_t locked_edges=0,locked_vertices=0;
    for(auto e:mesh.edges()) {
      if(CGAL::is_border(e,mesh)) ec[e]=true;
      if(ec[e]) { ++locked_edges; auto h=mesh.halfedge(e); vc[mesh.source(h)]=true; vc[mesh.target(h)]=true; }
    }
    using Item=std::pair<double,std::size_t>;
    std::priority_queue<Item,std::vector<Item>,std::greater<Item>> queue;
    for(auto v:mesh.vertices()) if(vc[v]) { distance[v]=0; queue.emplace(0,v.idx()); ++locked_vertices; }
    while(!queue.empty()) {
      auto [d,id]=queue.top(); queue.pop(); Mesh::Vertex_index v(id);
      if(d!=distance[v] || d>=1.) continue;
      for(auto h:CGAL::halfedges_around_target(v,mesh)) {
        auto neighbor=mesh.source(h);
        double next=d+std::sqrt(CGAL::to_double(CGAL::squared_distance(mesh.point(v),mesh.point(neighbor))));
        if(next<1. && next<distance[neighbor]) { distance[neighbor]=next; queue.emplace(next,neighbor.idx()); }
      }
    }
    double minimum=.7,maximum=.2;
    for(auto v:mesh.vertices()) { size[v]=.7-.5*std::min(1.,distance[v]); minimum=std::min(minimum,size[v]); maximum=std::max(maximum,size[v]); }
    Locked_distance_sizing sizing{size}; std::size_t oversize=0;
    for(auto e:mesh.edges()) if(ec[e]) { auto h=mesh.halfedge(e); if(sizing.is_too_long(mesh.source(h),mesh.target(h),mesh)) ++oversize; }
    std::size_t initial_vertices=mesh.number_of_vertices(),initial_faces=mesh.number_of_faces();
    double setup_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    bool executed=false;
    if(!preflight && !oversize) {
      PMP::isotropic_remeshing(selected,sizing,mesh,
        CGAL::parameters::edge_is_constrained_map(ec).vertex_is_constrained_map(vc)
          .protect_constraints(true).relax_constraints(false).number_of_iterations(3)
          .number_of_relaxation_steps(1).do_project(true));
      if(!CGAL::IO::write_polygon_mesh(argv[3],mesh,CGAL::parameters::stream_precision(17))) return 6;
      executed=true;
    }
    double final_min=.7,final_max=.2;
    for(auto v:mesh.vertices()) { final_min=std::min(final_min,size[v]); final_max=std::max(final_max,size[v]); }
    rusage usage{};getrusage(RUSAGE_SELF,&usage);
    std::uint64_t rss=usage.ru_maxrss;
#ifndef __APPLE__
    rss*=1024;
#endif
    std::ofstream report(argv[4]);
    report<<std::setprecision(17)<<"{\"input_vertices\":"<<initial_vertices<<",\"input_faces\":"<<initial_faces
      <<",\"vertices\":"<<mesh.number_of_vertices()<<",\"faces\":"<<mesh.number_of_faces()
      <<",\"protected_faces\":"<<protected_faces.size()<<",\"locked_edges\":"<<locked_edges<<",\"locked_vertices\":"<<locked_vertices
      <<",\"initial_target_min_mm\":"<<minimum<<",\"initial_target_max_mm\":"<<maximum
      <<",\"final_target_min_mm\":"<<final_min<<",\"final_target_max_mm\":"<<final_max
      <<",\"oversize_locked_edges\":"<<oversize<<",\"remesher_executed\":"<<(executed?"true":"false")
      <<",\"setup_seconds\":"<<setup_seconds<<",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()
      <<",\"peak_rss_bytes\":"<<rss<<"}\n";
    return oversize?5:0;
  } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 7; }
}
