// Read-only final-state diagnostics. No SMS run(), queue, collapse or mesh export.
#define main preserved_quality_patch_entrypoint
#include "quality_patch.cpp"
#undef main
#include <CGAL/Polyhedral_envelope.h>
#include <CGAL/Surface_mesh_simplification/Edge_collapse_visitor_base.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Bounded_normal_change_filter.h>
#include <boost/optional.hpp>
#include <algorithm>
#include <csignal>
#include <map>
#include <limits>
#include <unistd.h>

std::ofstream* probe_output=nullptr;
std::size_t probe_u=0,probe_v=0,probe_endpoint_origin=std::numeric_limits<std::size_t>::max();
const char* probe_phase="setup";
void probe_start(const char* event) {
  *probe_output<<"{\"event\":\""<<event<<"\",\"phase\":\""<<probe_phase
    <<"\",\"edge_current_ids\":["<<probe_u<<","<<probe_v<<"],\"endpoint_original_id\":";
  if(probe_endpoint_origin==std::numeric_limits<std::size_t>::max())*probe_output<<"null";
  else *probe_output<<probe_endpoint_origin;
}
void probe_end() {
  *probe_output<<"}"<<std::endl;
  if(!*probe_output)throw std::runtime_error("Diagnostic stream failed");
}
void probe_event(const char* event) { probe_start(event);probe_end(); }
template<class Q> void probe_quality(const Q& before,const Q& after) {
  probe_start("placement.quality_values");
  *probe_output<<",\"before_bad\":"<<before.bad<<",\"after_bad\":"<<after.bad
    <<",\"before_minimum\":"<<before.minimum<<",\"after_minimum\":"<<after.minimum;
  probe_end();
}
void probe_pair(const char* event,bool passed,double larger,double smaller,
                const Point& p0,const Point& p1,const Point& p2,const Point& p3) {
  probe_start(event);*probe_output<<",\"passed\":"<<(passed?"true":"false")
    <<",\"larger_squared_cross_norm\":"<<larger<<",\"smaller_squared_cross_norm\":"<<smaller
    <<",\"ordered_points_mm\":[";
  bool comma=false;for(const auto& p:{p0,p1,p2,p3}) {
    if(comma)*probe_output<<",";comma=true;
    *probe_output<<"["<<p.x()<<","<<p.y()<<","<<p.z()<<"]";
  }
  *probe_output<<"]";probe_end();
}
#define CGAL962_PROBE_EVENT(label) probe_event(label)
#define CGAL962_PROBE_PAIR(...) probe_pair(__VA_ARGS__)
#ifdef CGAL_SURFACE_MESH_SIMPLIFICATION_DETAIL_EDGE_COLLAPSE_H
#error An earlier internal SMS header would bypass the pinned diagnostic companion.
#endif
#include "installed-Edge_collapse-probe.h"
#include <CGAL/Surface_mesh_simplification/edge_collapse.h>
#include "endpoint003-guards-probe.hpp"
#if defined(CGAL_SURFACE_SIMPLIFICATION_ENABLE_TRACE)
#error Full-mesh SMS tracing is outside this fixed probe.
#endif

namespace CGAL { namespace Surface_mesh_simplification {
// The sole friend entry added to the pinned header. No queue/collapse accessor.
struct Endpoint_final_probe_access {
  template<class A> static typename A::Profile profile(A& a,typename A::halfedge_descriptor h) {
    return a.create_profile(h);
  }
  template<class A> static bool topology(A& a,const typename A::Profile& p) {
    return a.is_collapse_topologically_valid(p);
  }
  template<class A> static bool geometry(A& a,const typename A::Profile& p,typename A::Placement_type point) {
    return a.is_collapse_geometrically_valid(p,point);
  }
};
}}
template<class Key> struct Probe_index_map {
  using key_type=Key;using value_type=std::size_t;using reference=std::size_t;
  using category=boost::readable_property_map_tag;
  friend std::size_t get(const Probe_index_map&,Key key) { return key.idx(); }
};
struct Probe_point_map {
  using key_type=Vertex;using value_type=Point;using reference=const Point&;
  using category=boost::readable_property_map_tag;
  const Mesh* mesh;
  friend const Point& get(const Probe_point_map& map,Vertex v) { return map.mesh->point(v); }
};

int main(int argc,char** argv) {
  try {
    if(argc!=6)throw std::runtime_error("Usage: probe original.bin final.bin origins.u64 target-pairs.u64 fresh-output-directory");
    fs::path output=argv[5];
    if(fs::exists(output)||fs::is_symlink(output)||!fs::create_directory(output))
      throw std::runtime_error("Fresh diagnostic directory required");
    const Mesh original=read_surface(argv[1]);Mesh current=read_surface(argv[2]);
    if(fs::file_size(argv[3])!=8*current.number_of_vertices())throw std::runtime_error("Complete origin map required");
    std::ifstream input(argv[3],std::ios::binary);std::vector<std::size_t> origins;
    std::vector<bool> seen(original.num_vertices(),false);
    for(auto v:current.vertices()) {
      auto id=read_value<std::uint64_t>(input);
      if(id>=original.num_vertices()||seen[id]||current.point(v)!=original.point(Vertex(id)))
        throw std::runtime_error("Unique exact original-coordinate association required");
      origins.push_back(id);seen[id]=true;
    }
    std::vector<bool> seeds(original.num_vertices(),false),source_fixed(original.num_vertices(),false);
    std::size_t seed_faces=0;std::vector<Face> reference_faces;
    for(auto f:original.faces())if(triangle_quality(original,f)<2.0/29.0) {
      ++seed_faces;for(auto v:vertices(original,f))seeds[v.idx()]=true;
    }
    for(auto f:original.faces()) {
      auto v=vertices(original,f);bool inside=seeds[v[0].idx()]||seeds[v[1].idx()]||seeds[v[2].idx()];
      if(inside)reference_faces.push_back(f);
      else for(auto id:v)source_fixed[id.idx()]=true;
    }
    for(auto v:original.vertices())if(original.point(v).x()==-76.0||original.point(v).x()==76.0)source_fixed[v.idx()]=true;
    auto fixed=current.add_property_map<Vertex,bool>("v:probe-fixed",false).first;
    for(auto v:current.vertices())fixed[v]=source_fixed[origins[v.idx()]];
    auto constrained=current.add_property_map<Mesh::Edge_index,bool>("e:probe-constrained",false).first;
    for(auto e:current.edges()) {
      auto h=current.halfedge(e);constrained[e]=fixed[current.source(h)]&&fixed[current.target(h)];
    }
    std::size_t pair_count=fs::file_size(argv[4])/16;
    if(fs::file_size(argv[4])%16||(pair_count!=1&&pair_count!=135))throw std::runtime_error("One fixture or135 exact target pairs required");
    using H=Mesh::Halfedge_index;using Pair=std::pair<std::size_t,std::size_t>;
    std::map<Pair,H> targets;std::ifstream edges(argv[4],std::ios::binary);
    Pair previous{0,0};
    for(std::size_t i=0;i<pair_count;++i) {
      auto u=read_value<std::uint64_t>(edges),v=read_value<std::uint64_t>(edges);Pair key{u,v};
      if(u>=v||v>=current.num_vertices()||(i&&key<=previous))throw std::runtime_error("Strict sorted unique current-ID pairs required");
      targets.emplace(key,Mesh::null_halfedge());previous=key;
    }
    for(auto e:current.edges()) {
      auto h=current.halfedge(e);auto u=current.source(h).idx(),v=current.target(h).idx();
      auto found=targets.find({std::min(u,v),std::max(u,v)});
      if(found!=targets.end())found->second=u<v?h:current.opposite(h);
    }
    for(const auto& entry:targets)if(entry.second==Mesh::null_halfedge())throw std::runtime_error("Target is not an actual saved edge");
    if(pair_count==135&&(seed_faces!=744||reference_faces.size()!=4704||
       std::count(source_fixed.begin(),source_fixed.end(),true)!=900845))throw std::runtime_error("Bound original head mask differs");
    CGAL::Polyhedral_envelope<Kernel> envelope(reference_faces,original,finest_budget_mm);
    Endpoint_placement placement{&current,&fixed,&origins,&envelope};Quality_cost cost{&placement};Finest_stop stop;
    Kernel traits;Probe_index_map<Vertex> vim;Probe_point_map vpm{&current};Probe_index_map<H> him;
    SMS::internal::Dummy_filter ignore;SMS::Edge_collapse_visitor_base<Mesh> visitor;
    using A=SMS::EdgeCollapse<Mesh,Kernel,Finest_stop,decltype(vim),decltype(vpm),decltype(him),
      decltype(constrained),Quality_cost,Endpoint_placement,decltype(ignore),decltype(visitor),false>;
    // All referenced objects outlive A. Constructor initializes traits/maps/border/angle.
    // Queue arrays/counters stay unused; never call run(), collect(), loop() or cost().
    A algorithm(current,traits,stop,vim,vpm,him,constrained,cost,placement,ignore,visitor);
    std::ofstream stream(output/"events.jsonl");if(!stream)throw std::runtime_error("Fresh diagnostic output failed");
    stream<<std::setprecision(17);probe_output=&stream;
    probe_start("setup");*probe_output<<",\"original_seed_faces\":"<<seed_faces
      <<",\"reference_faces\":"<<reference_faces.size()<<",\"fixed_source_vertices\":"
      <<std::count(source_fixed.begin(),source_fixed.end(),true)<<",\"budget_mm\":"<<finest_budget_mm;probe_end();
    using Access=SMS::Endpoint_final_probe_access;
    for(const auto& entry:targets) {
      probe_u=entry.first.first;probe_v=entry.first.second;
      probe_endpoint_origin=std::numeric_limits<std::size_t>::max();
      auto profile=Access::profile(algorithm,entry.second);probe_phase="final_topology";
      bool topology=Access::topology(algorithm,profile);
      probe_phase="independent_final_placement";auto choice=placement.choose(profile);
      boost::optional<bool> geometry;
      if(choice&&topology) {
        probe_endpoint_origin=choice->origin;probe_phase="final_ordinary_geometry";
        geometry=Access::geometry(algorithm,profile,boost::optional<Point>(choice->point));
      } else {probe_phase="final_ordinary_geometry";probe_event("ordinary.not_evaluated_no_choice_or_topology");}
      probe_phase="final_result";
      if(choice)probe_endpoint_origin=choice->origin;
      probe_start("final_profile_result");*probe_output<<",\"topology\":"<<(topology?"true":"false")
        <<",\"choice_present\":"<<(choice?"true":"false")<<",\"ordinary_geometry\":";
      if(geometry)*probe_output<<(*geometry?"true":"false");else *probe_output<<"null";
      probe_end();
    }
    probe_phase="complete";probe_endpoint_origin=std::numeric_limits<std::size_t>::max();
    probe_start("complete");*probe_output<<",\"target_count\":"<<targets.size()
      <<",\"SMS_run_called\":false,\"mesh_exported\":false,\"historical_veto_identified\":false"
      <<",\"solver_admission\":false,\"engineering_accepted\":false";probe_end();
    stream.close();probe_output=nullptr;if(!stream)throw std::runtime_error("Final diagnostic close failed");
    return 0;
  }catch(const std::exception& e) {std::cerr<<"Probe refusal: "<<e.what()<<std::endl;return 2;}
}
