// Read-only scalar quality and affected-neighbor screen. No candidate writes.
#include "native_prefix.hpp"
#include <limits>
#include <set>

using Row=std::array<std::size_t,3>;
constexpr auto NO_SOURCE=std::numeric_limits<std::uint64_t>::max();
Row oriented(Row a) { return std::min({a,Row{a[1],a[2],a[0]},Row{a[2],a[0],a[1]}}); }
Row row(const Mesh& m,Face f) {
  auto v=vertices(m,f);return {v[0].idx(),v[1].idx(),v[2].idx()};
}
bool same_bits(const Point& a,const Point& b) {
  std::array<double,3> x{a.x(),a.y(),a.z()},y{b.x(),b.y(),b.z()};
  return std::memcmp(x.data(),y.data(),sizeof(x))==0;
}
std::vector<std::uint64_t> ids(const fs::path& path,std::size_t count) {
  if(fs::is_symlink(path)||!fs::is_regular_file(path)||fs::file_size(path)!=8*count)
    throw std::runtime_error("Exact raw u64 provenance length required");
  std::ifstream in(path,std::ios::binary);std::vector<std::uint64_t> out;out.reserve(count);
  for(std::size_t i=0;i<count;++i)out.push_back(read_value<std::uint64_t>(in));
  return out;
}
std::string quote(const std::string& value) {
  std::ostringstream s;s<<'"';for(unsigned char c:value) {
    if(c=='"'||c=='\\')s<<'\\'<<c;
    else if(c<32)s<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;
    else s<<c;
  }s<<'"';return s.str();
}
template<class T> void list(std::ostream& s,const std::vector<T>& a) {
  s<<'[';bool comma=false;for(auto x:a){if(comma)s<<',';comma=true;s<<x;}s<<']';
}
struct Result {
  std::string stage="input";Quality before,after;bool q_observed=false,neighbors_observed=false;
  std::size_t nv=0,nf=0,retained=0,created=0,old_faces=0,new_faces=0,affected=0,pairs=0,ratio=0,dihedral=0;
  std::vector<std::size_t> poor_sample,ratio_sample,dihedral_sample;
};
void emit(const fs::path& out,const Result& r,const std::string& status,const std::string& reason) {
  if(fs::exists(out/"report.json")||fs::is_symlink(out/"report.json"))throw std::runtime_error("Existing report preserved");
  std::ofstream s(out/"report.json",std::ios::out|std::ios::trunc);
  s<<std::setprecision(17)<<"{\"schema\":\"962-read-only-native-quality-neighbors/v1\",\"status\":"<<quote(status)
   <<",\"stage\":"<<quote(r.stage)<<",\"reason\":"<<quote(reason)<<",\"CGAL\":"<<quote(CGAL_VERSION_STR)
   <<",\"vertices\":"<<r.nv<<",\"triangles\":"<<r.nf<<",\"retained_coordinate_origins\":"<<r.retained
   <<",\"new_coordinate_sentinels\":"<<r.created<<",\"old_face_preimages\":"<<r.old_faces
   <<",\"new_face_sentinels\":"<<r.new_faces<<",\"affected_faces\":"<<r.affected
   <<",\"all_face_quality_observed\":"<<(r.q_observed?"true":"false")<<",\"original_quality\":";
  if(r.q_observed)s<<json_quality(r.before);else s<<"null";
  s<<",\"candidate_quality\":";if(r.q_observed)s<<json_quality(r.after);else s<<"null";
  s<<",\"first_poor_face_IDs_at_most_16\":";list(s,r.poor_sample);
  s<<",\"affected_neighbor_policy_observed\":"<<(r.neighbors_observed?"true":"false")
   <<",\"affected_neighbor_pairs\":"<<r.pairs<<",\"area_ratio_failures\":"<<r.ratio
   <<",\"dihedral_failures\":"<<r.dihedral<<",\"first_area_ratio_edge_IDs_at_most_16\":";list(s,r.ratio_sample);
  s<<",\"first_dihedral_edge_IDs_at_most_16\":";list(s,r.dihedral_sample);
  s<<",\"necessary_quality_gate_passed\":"<<(r.q_observed&&r.after.bad==0?"true":"false")
   <<",\"affected_neighbor_policy_passed\":"<<(r.neighbors_observed&&!r.ratio&&!r.dihedral?"true":"false")
   <<",\"necessary_q_threshold_expression\":\"2.0/29.0\",\"squared_area_ratio_strict_bound\":100000000"
   <<",\"near_opposed_normal_angle_degrees\":1,\"native_predicate_order\":\"ordinary(a,d,b,c) exactly as source003\""
   <<",\"Mesh_2_stronger_shape_criterion_evaluated\":false,\"global_self_intersections_evaluated\":false"
   <<",\"global_vertex_links_components_Euler_evaluated\":false,\"distance_features_envelope_evaluated\":false"
   <<",\"surface_generated_or_modified\":false,\"candidate_exported\":false,\"head_surface_or_solver_admitted\":false"
   <<",\"manufacturing_authorized\":false}\n";
  s.close();if(!s)throw std::runtime_error("Report output failed");
}
int main(int argc,char** argv) {
  fs::path out;Result r;bool output_owned=false;
  try {
    if(argc!=6)throw std::runtime_error("Usage: audit-native original.bin candidate.bin origins.u64 face-source.u64 fresh-output-directory");
    out=argv[5];if(fs::exists(out)||fs::is_symlink(out)){out.clear();throw std::runtime_error("Fresh output required");}
    for(int i=1;i<=4;++i)if(fs::is_symlink(argv[i])||!fs::is_regular_file(argv[i]))throw std::runtime_error("Regular immutable inputs required");
    std::cerr<<"begin read immutable original and candidate\n"<<std::flush;
    const Mesh original=read_surface(argv[1]),candidate=read_surface(argv[2]);
    r.nv=candidate.num_vertices();r.nf=candidate.num_faces();
    const bool head=r.nv==871731&&r.nf==1743878;
    if(head?(original.num_vertices()!=869355||original.num_faces()!=1739126)
           :(original.num_vertices()!=4||original.num_faces()!=4||r.nv!=4||r.nf!=4))
      throw std::runtime_error("Only bound assembled-head or literal tetra counts permitted");
    const auto origins=ids(argv[3],r.nv),sources=ids(argv[4],r.nf);
    std::vector<bool> seen_vertex(original.num_vertices(),false),seen_face(original.num_faces(),false),affected(r.nf,false);
    for(auto v:candidate.vertices()) {
      auto id=origins[v.idx()];if(id==NO_SOURCE){++r.created;continue;}
      if(id>=original.num_vertices()||seen_vertex[id]||!same_bits(candidate.point(v),original.point(Vertex(id))))
        throw std::runtime_error("Old coordinate origin must be unique, bounded and byte-exact");
      seen_vertex[id]=true;++r.retained;
    }
    for(auto f:candidate.faces()) {
      auto id=sources[f.idx()];bool changed=id==NO_SOURCE;
      if(changed)++r.new_faces;
      else {
        if(id>=original.num_faces()||seen_face[id])throw std::runtime_error("Old face preimage must be unique and bounded");
        seen_face[id]=true;++r.old_faces;auto v=row(candidate,f);Row old_ids{};
        for(int k=0;k<3;++k){old_ids[k]=origins[v[k]];if(old_ids[k]==NO_SOURCE)changed=true;}
        if(!changed)changed=oriented(old_ids)!=oriented(row(original,Face(id)));
      }
      affected[f.idx()]=changed;r.affected+=changed;
    }
    if(head&&(r.retained!=868639||r.created!=3092||r.old_faces!=1734940||r.new_faces!=8938||r.affected!=9702))
      throw std::runtime_error("Exact assembled-head provenance counts changed");
    if(!fs::create_directory(out))throw std::runtime_error("Fresh output required");output_owned=true;
    r.stage="all_face_quality";std::cerr<<"begin all-face native quality\n"<<std::flush;
    r.before=quality(original);r.after=quality(candidate);r.q_observed=true;
    if(r.before.faces!=original.num_faces()||r.after.faces!=r.nf)throw std::runtime_error("Complete quality coverage required");
    if(r.after.bad)for(auto f:candidate.faces())if(r.poor_sample.size()<16&&triangle_quality(candidate,f)<2.0/29.0)r.poor_sample.push_back(f.idx());
    std::cerr<<"end all-face native quality\nbegin complete affected-neighbor scan\n"<<std::flush;
    r.stage="affected_neighbors";
    for(auto e:candidate.edges()) {
      auto h=candidate.halfedge(e),op=candidate.opposite(h);auto f1=candidate.face(h),f2=candidate.face(op);
      if(f1==Mesh::null_face()||f2==Mesh::null_face())throw std::runtime_error("Closed two-face edge incidence required");
      if(!affected[f1.idx()]&&!affected[f2.idx()])continue;
      const auto &a=candidate.point(candidate.source(h)),&b=candidate.point(candidate.target(h)),
        &c=candidate.point(candidate.target(candidate.next(h))),&d=candidate.point(candidate.target(candidate.next(op)));
      ++r.pairs;auto failure=ordinary(a,d,b,c);
      if(failure==1){++r.ratio;if(r.ratio_sample.size()<16)r.ratio_sample.push_back(e.idx());}
      else if(failure==2){++r.dihedral;if(r.dihedral_sample.size()<16)r.dihedral_sample.push_back(e.idx());}
      else if(failure!=0)throw std::runtime_error("Unexpected frozen predicate result");
    }
    r.neighbors_observed=true;r.stage="complete";std::cerr<<"end complete affected-neighbor scan\n"<<std::flush;
    const bool passed=!r.after.bad&&!r.ratio&&!r.dihedral;
    emit(out,r,passed?"native_q_and_affected_neighbors_passed_only":"native_q_or_affected_neighbors_rejected",
      passed?"Necessary scalar screens only; independent gates pending":"At least one frozen necessary scalar screen failed");
    return passed?0:3;
  } catch(const std::exception& e) {
    if(output_owned&&!out.empty()&&fs::is_directory(out)&&!fs::exists(out/"report.json"))try{emit(out,r,"error_no_acceptance",e.what());}catch(...){}
    std::cerr<<"native read-only audit error: "<<e.what()<<'\n';return 2;
  }
}
