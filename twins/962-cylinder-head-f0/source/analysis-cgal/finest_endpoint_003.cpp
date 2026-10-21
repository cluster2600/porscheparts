// Version003 preparation: immutable original-patch envelope, no mesh admission.
// Reuse the pinned project reader/writer/quality code without invoking its pass.
#define main preserved_quality_patch_entrypoint
#include "quality_patch.cpp"
#undef main
#include <CGAL/Polyhedral_envelope.h>
#include <CGAL/Surface_mesh_simplification/edge_collapse.h>
#include <CGAL/Surface_mesh_simplification/Edge_collapse_visitor_base.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Bounded_normal_change_filter.h>
#include <boost/optional.hpp>
#include <csignal>
#include <unistd.h>

namespace SMS=CGAL::Surface_mesh_simplification;
constexpr double finest_budget_mm=0.0625;
volatile std::sig_atomic_t finest_stop_requested=0;
void finest_stop(int) { finest_stop_requested=1; }

double point_quality(const Point& a,const Point& b,const Point& c) {
  auto u=b-a,v=c-a;
  return 2*std::sqrt(3.0)*std::sqrt(CGAL::cross_product(u,v).squared_length())/
    (u.squared_length()+v.squared_length()+(v-u).squared_length());
}
struct Local_quality { std::size_t bad=0;double minimum=1; };
bool local_improves(const Local_quality& before,const Local_quality& after) {
  return after.bad<before.bad&&after.minimum>=before.minimum;
}
struct Endpoint_choice {
  Point point;std::size_t origin;Local_quality before,after;
};
using Fixed_map=Mesh::Property_map<Vertex,bool>;
struct Endpoint_placement {
  const Mesh* mesh;
  const Fixed_map* fixed;
  const std::vector<std::size_t>* origins;
  const CGAL::Polyhedral_envelope<Kernel>* envelope;
  template<class Profile> boost::optional<Endpoint_choice> choose(const Profile& profile) const {
    if(finest_stop_requested||(*fixed)[profile.v0()]||(*fixed)[profile.v1()]
       ||!profile.left_face_exists()||!profile.right_face_exists())return boost::none;
    const auto& fan=profile.triangles();
    if(fan.size()<=2)return boost::none;
    Local_quality before;
    for(const auto& t:fan) {
      double q=point_quality(mesh->point(t.v0),mesh->point(t.v1),mesh->point(t.v2));
      if(!std::isfinite(q)||q<=0)throw std::runtime_error("Invalid current triangle");
      before.bad+=q<2.0/29.0;before.minimum=std::min(before.minimum,q);
    }
    if(!before.bad)return boost::none;
    boost::optional<Endpoint_choice> best;
    SMS::Bounded_normal_change_filter<> normal_filter;
    for(auto endpoint:{profile.v0(),profile.v1()}) {
      const Point p=mesh->point(endpoint);
      if(!normal_filter(profile,boost::optional<Point>(p))||!(*envelope)(p))continue;
      Local_quality after;bool admissible=true;
      // CGAL5.6 puts the two removed edge faces first. In each remaining
      // triangle, v1 is the endpoint being replaced, not a link vertex.
      for(std::size_t i=2;i<fan.size();++i) {
        const auto& t=fan[i];const auto& a=mesh->point(t.v0);const auto& c=mesh->point(t.v2);
        double q=point_quality(a,p,c);
        if(!std::isfinite(q)||q<=0||!(*envelope)(a,p,c)) { admissible=false;break; }
        after.bad+=q<2.0/29.0;after.minimum=std::min(after.minimum,q);
      }
      if(!admissible||!local_improves(before,after))continue;
      Endpoint_choice current{p,(*origins)[endpoint.idx()],before,after};
      if(!best||current.after.bad<best->after.bad
         ||(current.after.bad==best->after.bad&&current.after.minimum>best->after.minimum)
         ||(current.after.bad==best->after.bad&&current.after.minimum==best->after.minimum
            &&current.origin<best->origin))best=current;
    }
    return best;
  }
  template<class Profile> boost::optional<typename Profile::Point> operator()(const Profile& p) const {
    auto choice=choose(p);if(!choice)return boost::none;return choice->point;
  }
};
struct Quality_cost {
  const Endpoint_placement* placement;
  template<class Profile> boost::optional<typename Profile::FT> operator()(
    const Profile& profile,const boost::optional<typename Profile::Point>& point)const {
    if(!point)return boost::none;auto c=placement->choose(profile);
    if(!c)return boost::none;
    return -static_cast<double>(c->before.bad-c->after.bad);
  }
};
struct Finest_stop {
  template<class FT,class Profile> bool operator()(const FT&,const Profile&,std::size_t,std::size_t)const {
    return finest_stop_requested!=0;
  }
};
struct Endpoint_visitor:SMS::Edge_collapse_visitor_base<Mesh> {
  const Endpoint_placement* placement;
  std::vector<std::size_t>* origins;
  std::size_t* collapses;
  std::size_t pending_origin=0;
  void OnCollapsing(const Profile& profile,const boost::optional<Point>& point) {
    auto c=placement->choose(profile);
    if(!point||!c||*point!=c->point)throw std::runtime_error("Stale or inadmissible placement");
    pending_origin=c->origin;
  }
  void OnCollapsed(const Profile&,const vertex_descriptor& kept) {
    (*origins)[kept.idx()]=pending_origin;++*collapses;
  }
};

// Flushed scalar progress only; a stage never implies an accepted result.
void finest_stage(const char* stage,const Mesh* mesh=nullptr,
                  const std::vector<Face>* reference=nullptr,
                  std::size_t seed_faces=0,std::size_t reference_vertices=0) {
  std::cout<<"{\"schema\":\"962-endpoint003-progress/v1\",\"stage\":\""<<stage<<"\"";
  if(mesh)std::cout<<",\"vertices\":"<<mesh->number_of_vertices()
                   <<",\"faces\":"<<mesh->number_of_faces();
  if(reference)std::cout<<",\"seed_faces\":"<<seed_faces
                       <<",\"reference_faces\":"<<reference->size()
                       <<",\"reference_vertices\":"<<reference_vertices;
  std::cout<<"}"<<std::endl;
}
void write_reference_ids(const fs::path& path,const std::vector<std::uint64_t>& ids) {
  if(fs::exists(path)||fs::is_symlink(path))throw std::runtime_error("Existing reference IDs preserved");
  std::ofstream stream(path,std::ios::binary);
  for(auto id:ids)for(unsigned shift=0;shift<64;shift+=8)
    stream.put(static_cast<char>((id>>shift)&0xff));
  stream.close();if(!stream)throw std::runtime_error("Reference ID output failed");
}

int main(int argc,char** argv) {
  try {
    if(argc!=3)throw std::runtime_error("Usage: finest-endpoint original.bin fresh-output-directory");
    fs::path output=argv[2];
    if(!fs::create_directory(output))throw std::runtime_error("Output directory must be new");
    finest_stage("original_import_begin");
    const Mesh original=read_surface(argv[1]);
    finest_stage("original_import_complete",&original);
    finest_stage("candidate_copy_begin",&original);
    Mesh candidate=original;
    finest_stage("candidate_copy_complete",&candidate);
    finest_stage("original_quality_scan_begin",&original);
    const Quality before=quality(original);
    finest_stage("original_quality_scan_complete",&original);
    std::vector<bool> seeds(original.num_vertices(),false),in_patch(original.num_faces(),false);
    std::size_t seed_faces=0,patch_faces=0;
    for(auto f:original.faces())if(triangle_quality(original,f)<2.0/29.0) {
      ++seed_faces;for(auto v:vertices(original,f))seeds[v.idx()]=true;
    }
    std::vector<Face> reference_faces;
    std::vector<bool> reference_vertex(original.num_vertices(),false);
    auto fixed=candidate.add_property_map<Vertex,bool>("v:finest-fixed",false).first;
    for(auto f:original.faces()) {
      auto v=vertices(original,f);bool inside=seeds[v[0].idx()]||seeds[v[1].idx()]||seeds[v[2].idx()];
      in_patch[f.idx()]=inside;patch_faces+=inside;
      if(inside) {
        reference_faces.push_back(f); // Exact immutable original face order.
        for(auto id:v)reference_vertex[id.idx()]=true;
      }
      if(!inside)for(auto id:v)fixed[id]=true;
    }
    for(auto v:original.vertices())if(original.point(v).x()==-76.0||original.point(v).x()==76.0)fixed[v]=true;
    std::vector<std::uint64_t> reference_face_ids,reference_vertex_ids;
    for(auto f:reference_faces)reference_face_ids.push_back(f.idx());
    for(auto v:original.vertices())if(reference_vertex[v.idx()])reference_vertex_ids.push_back(v.idx());
    write_reference_ids(output/"patch-reference-face-ids.u64",reference_face_ids);
    write_reference_ids(output/"patch-reference-vertex-ids.u64",reference_vertex_ids);
    finest_stage("patch_reference_exported",&original,&reference_faces,seed_faces,reference_vertex_ids.size());
    auto constrained=candidate.add_property_map<Mesh::Edge_index,bool>("e:finest-fixed",false).first;
    for(auto e:candidate.edges()) {
      auto h=candidate.halfedge(e);
      constrained[e]=fixed[candidate.source(h)]&&fixed[candidate.target(h)];
      if(candidate.point(candidate.source(h))==candidate.point(candidate.target(h)))
        throw std::runtime_error("Zero-length edge would bypass the ordinary SMS filters");
    }
    std::vector<std::size_t> origins(original.num_vertices());
    for(auto v:original.vertices())origins[v.idx()]=v.idx();
    // A subset of original triangles is a conservative distance reference:
    // distance(x,complete_original) <= distance(x,original_patch).
    // Build once; never replace these immutable faces with candidate triangles.
    finest_stage("patch_envelope_build_begin",&original,&reference_faces,seed_faces,reference_vertex_ids.size());
    CGAL::Polyhedral_envelope<Kernel> envelope(reference_faces,original,finest_budget_mm);
    finest_stage("patch_envelope_build_complete",&original,&reference_faces,seed_faces,reference_vertex_ids.size());
    Endpoint_placement placement{&candidate,&fixed,&origins,&envelope};
    std::size_t collapses=0;Endpoint_visitor visitor;
    visitor.placement=&placement;visitor.origins=&origins;visitor.collapses=&collapses;
    std::signal(SIGALRM,finest_stop);std::signal(SIGTERM,finest_stop);alarm(285);
    finest_stage("SMS_begin",&candidate);
    SMS::edge_collapse(candidate,Finest_stop(),CGAL::parameters::get_cost(Quality_cost{&placement})
      .get_placement(placement).edge_is_constrained_map(constrained).visitor(visitor));
    alarm(0);
    finest_stage("SMS_returned",&candidate);
    const Quality after=quality(candidate);
    bool fixed_same=true,outside_same=true,source_points_exact=true;
    for(auto v:original.vertices())if(fixed[v]
      &&(candidate.is_removed(v)||candidate.point(v)!=original.point(v)))fixed_same=false;
    for(auto f:original.faces())if(!in_patch[f.idx()]
      &&(candidate.is_removed(f)||canonical_face(original,f)!=canonical_face(candidate,f)))outside_same=false;
    for(auto v:candidate.vertices())if(candidate.point(v)!=original.point(Vertex(origins[v.idx()])))source_points_exact=false;
    bool valid=CGAL::is_closed(candidate)&&CGAL::is_triangle_mesh(candidate)&&CGAL::is_valid_polygon_mesh(candidate);
    bool improve=after.bad<before.bad&&after.minimum>=before.minimum;
    bool counts=original.number_of_vertices()==candidate.number_of_vertices()+collapses
      &&original.number_of_faces()==candidate.number_of_faces()+2*collapses;
    bool proposed=!finest_stop_requested&&improve&&valid&&counts&&fixed_same&&outside_same&&source_points_exact;
    finest_stage("result_export_begin",&candidate);
    write_surface(candidate,output/"proposed-surface.bin");
    // Export source-coordinate provenance in exactly the writer's vertex order.
    std::ofstream map(output/"vertex-coordinate-origins.u64",std::ios::binary);
    for(auto v:candidate.vertices())write_value<std::uint64_t>(map,origins[v.idx()]);
    map.close();if(!map)throw std::runtime_error("Origin map output failed");
    if(proposed)write_surface(candidate,output/"quality-candidate.bin");
    auto b=[](bool x){return x?"true":"false";};
    std::ostringstream report;
    report<<std::setprecision(17)<<"{\"schema\":\"962-finest-endpoint-trial/v1\",\"CGAL\":\""<<CGAL_VERSION_STR
      <<"\",\"status\":\""<<(proposed?"local_quality_candidate_independent_gates_pending":"rejected_or_bounded_original_preserved")
      <<"\",\"geometry_budget_mm\":"<<finest_budget_mm<<",\"source_seed_faces\":"<<seed_faces
      <<",\"original_patch_faces\":"<<patch_faces
      <<",\"envelope_reference_kind\":\"immutable_original_patch_faces\""
      <<",\"envelope_reference_face_count\":"<<reference_faces.size()
      <<",\"envelope_reference_vertex_count\":"<<reference_vertex_ids.size()
      <<",\"envelope_reference_face_ids\":\"patch-reference-face-ids.u64\""
      <<",\"envelope_reference_vertex_ids\":\"patch-reference-vertex-ids.u64\""
      <<",\"accepted_collapses\":"<<collapses
      <<",\"full_surface_before\":"<<json_quality(before)<<",\"full_surface_after\":"<<json_quality(after)
      <<",\"fixed_source_coordinates_exact\":"<<b(fixed_same)<<",\"exterior_oriented_faces_exact\":"<<b(outside_same)
      <<",\"retained_coordinates_are_exact_source_points\":"<<b(source_points_exact)
      <<",\"closed_valid_triangle_mesh\":"<<b(valid)<<",\"collapse_count_bookkeeping\":"<<b(counts)
      <<",\"full_quality_objective\":"<<b(improve)<<",\"soft_stop_requested\":"<<b(finest_stop_requested)
      <<",\"candidate_written\":"<<b(proposed)<<",\"source_master_altered\":false"
      <<",\"independent_bidirectional_distance_completed\":false,\"complete_semantic_constraint_map\":false"
      <<",\"independent_global_topology_and_intersections_completed\":false,\"solver_admission_established\":false"
      <<",\"head_physics_executed\":false,\"engineering_accepted\":false,\"manufacturing_authorized\":false}";
    std::ofstream stream(output/"report.json");stream<<report.str()<<"\n";stream.close();
    if(!stream)throw std::runtime_error("Report output failed");
    finest_stage("result_export_complete",&candidate);
    std::cout<<report.str()<<std::endl;return proposed?0:3;
  }catch(const std::exception& e){std::cerr<<"finest-endpoint failure: "<<e.what()<<std::endl;return 2;}
}
