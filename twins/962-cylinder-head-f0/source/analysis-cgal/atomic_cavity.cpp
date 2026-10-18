// Separate simultaneous quotient candidate. No SMS queue/intermediate collapses.
#define main preserved_quality_patch_entrypoint
#include "quality_patch.cpp"
#undef main
#include <CGAL/Polyhedral_envelope.h>
#include <CGAL/number_utils.h>
#include <algorithm>
#include <limits>
#include <map>
#include <numeric>
#include <set>

using Row=std::array<std::size_t,3>;
using Edge=std::pair<std::size_t,std::size_t>;
struct Rejected:std::runtime_error { using std::runtime_error::runtime_error; };
struct UF {
  std::vector<std::size_t> p;
  explicit UF(std::size_t n):p(n) { std::iota(p.begin(),p.end(),0); }
  std::size_t find(std::size_t v) { while(v!=p[v]) {p[v]=p[p[v]];v=p[v];}return v; }
  void join(std::size_t a,std::size_t b) {a=find(a);b=find(b);if(a!=b)p[std::max(a,b)]=std::min(a,b);}
};
bool same_point_bits(const Point& a,const Point& b) {
  std::array<double,3> x{a.x(),a.y(),a.z()},y{b.x(),b.y(),b.z()};return std::memcmp(x.data(),y.data(),sizeof(x))==0;
}
Row oriented(Row a) { return std::min({a,Row{a[1],a[2],a[0]},Row{a[2],a[0],a[1]}}); }
std::vector<Edge> pairs(const fs::path& path) {
  auto bytes=fs::file_size(path);if(!bytes||bytes%16||bytes>135*16)throw std::runtime_error("Invalid fixed pair file");
  std::ifstream in(path,std::ios::binary);std::vector<Edge> out;
  while(out.size()<bytes/16) {auto a=read_value<std::uint64_t>(in),b=read_value<std::uint64_t>(in);out.emplace_back(a,b);}
  if(!std::is_sorted(out.begin(),out.end())||std::adjacent_find(out.begin(),out.end())!=out.end())throw std::runtime_error("Sorted unique pair rows required");
  return out;
}
using Chain=std::map<Edge,long>;
void chain_add(Chain& c,Row t) {
  for(int i=0;i<3;++i) {auto a=t[i],b=t[(i+1)%3];Edge e{std::min(a,b),std::max(a,b)};c[e]+=a<b?1:-1;if(!c[e])c.erase(e);}
}
struct Topology {bool valid=false;std::size_t components=0;long long euler=0;};
Topology topology(const Mesh& m) {
  Topology s;if(!CGAL::is_closed(m)||!CGAL::is_triangle_mesh(m)||!CGAL::is_valid_polygon_mesh(m))return s;
  std::vector<std::size_t> incidence(m.num_vertices(),0);UF uf(m.num_vertices());
  for(auto f:m.faces())for(auto v:vertices(m,f))++incidence[v.idx()];
  for(auto e:m.edges()) {auto h=m.halfedge(e);uf.join(m.source(h).idx(),m.target(h).idx());}
  for(auto v:m.vertices()) {
    if(!incidence[v.idx()])return s;std::size_t count=0;
    for(auto h:CGAL::halfedges_around_target(m.halfedge(v),m)) {
      if(m.target(h)!=v||++count>incidence[v.idx()])return s;
    }
    if(count!=incidence[v.idx()])return s;if(uf.find(v.idx())==v.idx())++s.components;
  }
  s.euler=static_cast<long long>(m.number_of_vertices())-static_cast<long long>(m.number_of_edges())+static_cast<long long>(m.number_of_faces());s.valid=true;return s;
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
struct Record {
  std::string stage="setup";std::size_t input_vertices=0,input_faces=0,groups=0,dropped=0,affected_survivors=0,normals_failed=0,duplicates=0;
  std::size_t candidate_vertices=0,candidate_faces=0,bad=0,fixed_count=0,fixed_retained=0,reference_faces=0,patch_faces=0,envelope_failed=0,neighbor_pairs=0,ratio_failed=0,dihedral_failed=0;
  double minimum=std::numeric_limits<double>::quiet_NaN();bool inputs=false,candidate_built=false,quality_checked=false,normal=false,quality=false,topology=false,fixed=false,exterior=false,boundary=false,envelope=false,neighbors=false,exported=false;
  Topology old_topology,new_topology;
};
void report(const fs::path& out,const Record& r,const char* status,const std::string& reason) {
  if(out.empty()||!fs::is_directory(out))return;
  auto path=out/"report.json";if(fs::exists(path))throw std::runtime_error("Existing report preserved");
  std::ofstream s(path);s<<std::setprecision(17)<<"{\"status\":\""<<status<<"\",\"stage\":\""<<r.stage<<"\",\"reason\":\"";
  for(char c:reason) {if(c=='"'||c=='\\')s<<'\\';if(c=='\n')s<<"\\n";else s<<c;}
  s<<"\",\"input_vertices\":"<<r.input_vertices<<",\"input_faces\":"<<r.input_faces<<",\"groups\":"<<r.groups<<",\"dropped_faces\":"<<r.dropped
   <<",\"candidate_built\":"<<(r.candidate_built?"true":"false")<<",\"quality_checked\":"<<(r.quality_checked?"true":"false")<<",\"candidate_vertices\":"<<r.candidate_vertices<<",\"candidate_faces\":"<<r.candidate_faces<<",\"bad_faces\":"<<r.bad<<",\"minimum_quality\":";
  if(std::isfinite(r.minimum))s<<r.minimum;else s<<"null";
  s<<",\"affected_survivors\":"<<r.affected_survivors<<",\"normal_failures\":"<<r.normals_failed<<",\"duplicates\":"<<r.duplicates
   <<",\"fixed_source_vertices\":"<<r.fixed_count<<",\"fixed_retained\":"<<r.fixed_retained<<",\"original_reference_faces\":"<<r.reference_faces
   <<",\"candidate_patch_faces\":"<<r.patch_faces<<",\"envelope_failures\":"<<r.envelope_failed<<",\"final_affected_neighbor_pairs\":"<<r.neighbor_pairs
   <<",\"area_ratio_failures\":"<<r.ratio_failed<<",\"dihedral_failures\":"<<r.dihedral_failed
   <<",\"before_components\":"<<r.old_topology.components<<",\"after_components\":"<<r.new_topology.components
   <<",\"before_Euler\":"<<r.old_topology.euler<<",\"after_Euler\":"<<r.new_topology.euler<<",\"guards\":{";
  bool comma=false;for(auto x:{std::make_pair("inputs",r.inputs),{"normals",r.normal},{"global_quality",r.quality},{"topology_links_components_Euler",r.topology},{"fixed",r.fixed},{"exterior",r.exterior},{"patch_and_affected_boundary",r.boundary},{"original_triangle_envelope",r.envelope},{"final_affected_neighbor_policy",r.neighbors}}) {
    if(comma)s<<",";comma=true;s<<"\""<<x.first<<"\":"<<(x.second?"true":"false");
  }
  s<<"},\"exported\":"<<(r.exported?"true":"false")<<",\"candidate_file\":"<<(r.exported?"\"candidate.bin\"":"null")
   <<",\"origins_file\":"<<(r.exported?"\"vertex-coordinate-origins.u64\"":"null")
   <<",\"independent_distance_intersection_features_pending\":true,\"historical_SMS_veto_identified\":false,\"head_or_solver_admitted\":false,\"manufacturing_authorized\":false}\n";
  s.close();if(!s)throw std::runtime_error("Report write failed");
}
int main(int argc,char** argv) {
  fs::path out;Record r;
  try {
    if(argc!=7)throw std::runtime_error("Usage: atomic original current origins targets keepers fresh-output-directory");
    out=argv[6];if(fs::exists(out)||fs::is_symlink(out)||!fs::create_directory(out)) {out.clear();throw std::runtime_error("Fresh output required");}
    const Mesh original=read_surface(argv[1]),current=read_surface(argv[2]);r.input_vertices=current.num_vertices();r.input_faces=current.num_faces();r.stage="input_association";
    if(fs::file_size(argv[3])!=8*current.num_vertices())throw std::runtime_error("Complete origins required");
    std::ifstream oi(argv[3],std::ios::binary);std::vector<std::size_t> origins;std::vector<bool> seen(original.num_vertices(),false);
    for(auto v:current.vertices()) {auto id=read_value<std::uint64_t>(oi);if(id>=original.num_vertices()||seen[id]||!same_point_bits(current.point(v),original.point(Vertex(id))))throw std::runtime_error("Unique exact original coordinates required");origins.push_back(id);seen[id]=true;}
    std::vector<bool> seeds(original.num_vertices(),false),fixed(original.num_vertices(),false);std::vector<Face> reference;std::size_t seed_faces=0;
    for(auto f:original.faces())if(triangle_quality(original,f)<2.0/29.0) {++seed_faces;for(auto v:vertices(original,f))seeds[v.idx()]=true;}
    std::vector<Row> exterior;Chain original_boundary;
    for(auto f:original.faces()) {
      auto vs=vertices(original,f);Row ids{vs[0].idx(),vs[1].idx(),vs[2].idx()};bool inside=seeds[ids[0]]||seeds[ids[1]]||seeds[ids[2]];
      if(inside) {reference.push_back(f);chain_add(original_boundary,ids);}else {exterior.push_back(oriented(ids));for(auto v:ids)fixed[v]=true;}
    }
    for(auto v:original.vertices())if(original.point(v).x()==-76.0||original.point(v).x()==76.0)fixed[v.idx()]=true;
    r.fixed_count=std::count(fixed.begin(),fixed.end(),true);r.reference_faces=reference.size();
    for(std::size_t i=0;i<fixed.size();++i)if(fixed[i]&&!seen[i])throw std::runtime_error("Current omits original fixed vertex");
    auto targets=pairs(argv[4]),keepers=pairs(argv[5]);UF uf(current.num_vertices());std::set<Edge> target_set(targets.begin(),targets.end()),found;
    for(auto e:targets) {if(e.first>=e.second||e.second>=current.num_vertices())throw std::runtime_error("Valid target edge IDs required");uf.join(e.first,e.second);}
    for(auto e:current.edges()) {auto h=current.halfedge(e);Edge ids=std::minmax(current.source(h).idx(),current.target(h).idx());if(target_set.count(ids))found.insert(ids);}
    if(found!=target_set)throw std::runtime_error("Every target must be an actual edge");
    std::map<std::size_t,std::vector<std::size_t>> groups;
    for(auto e:targets)for(auto v:{e.first,e.second})groups[uf.find(v)].push_back(v);
    for(auto& g:groups) {auto& v=g.second;std::sort(v.begin(),v.end());v.erase(std::unique(v.begin(),v.end()),v.end());}
    r.groups=groups.size();bool head=targets.size()==135;
    if(head) {
      std::size_t n2=0,n4=0;for(const auto& g:groups) {n2+=g.second.size()==2;n4+=g.second.size()==4;}
      if(groups.size()!=132||n2!=131||n4!=1||seed_faces!=744||reference.size()!=4704||r.fixed_count!=900845)throw std::runtime_error("Frozen head groups/reference/fixed counts differ");
    }else if(groups.size()!=1||!((targets.size()==1&&groups.begin()->second.size()==2)||(targets.size()==4&&groups.begin()->second.size()==4)))throw std::runtime_error("Only fixed two/four-vertex fixtures permitted");
    if(keepers.size()!=groups.size())throw std::runtime_error("One keeper per component required");
    std::vector<std::size_t> map(current.num_vertices());std::iota(map.begin(),map.end(),0);std::vector<bool> member(current.num_vertices(),false);
    std::set<std::size_t> named_groups;
    for(auto k:keepers) {
      if(!named_groups.insert(k.first).second)throw std::runtime_error("Duplicate keeper component");
      auto g=groups.find(k.first);if(g==groups.end()||g->second.front()!=k.first||!std::binary_search(g->second.begin(),g->second.end(),k.second))throw std::runtime_error("Keeper must name exact component minimum and member");
      for(auto v:g->second) {if(fixed[origins[v]])throw Rejected("Mapped component touches original fixed vertex");map[v]=k.second;member[v]=true;}
    }
    r.old_topology=topology(current);if(!r.old_topology.valid)throw std::runtime_error("Current full links/topology invalid");r.inputs=true;r.stage="simultaneous_quotient";
    Quality before=quality(current);std::vector<Row> rows,unordered;std::vector<bool> affected,referenced(current.num_vertices(),false);Chain before_boundary,after_boundary;
    for(auto f:current.faces()) {
      auto vs=vertices(current,f);Row old{vs[0].idx(),vs[1].idx(),vs[2].idx()},t{map[old[0]],map[old[1]],map[old[2]]};bool a=member[old[0]]||member[old[1]]||member[old[2]];
      if(a)chain_add(before_boundary,Row{origins[old[0]],origins[old[1]],origins[old[2]]});
      if(t[0]==t[1]||t[0]==t[2]||t[1]==t[2]) {++r.dropped;continue;}
      const auto &p0=current.point(Vertex(t[0])),&p1=current.point(Vertex(t[1])),&p2=current.point(Vertex(t[2]));auto n=CGAL::cross_product(p1-p0,p2-p0);
      if(!std::isfinite(n.squared_length())||n.squared_length()<=0)throw Rejected("Degenerate surviving quotient triangle");
      if(a) {
        ++r.affected_survivors;auto oldn=CGAL::cross_product(current.point(vs[1])-current.point(vs[0]),current.point(vs[2])-current.point(vs[0]));if(!(oldn*n>0))++r.normals_failed;
        chain_add(after_boundary,Row{origins[t[0]],origins[t[1]],origins[t[2]]});
      }
      rows.push_back(t);affected.push_back(a);Row key=t;std::sort(key.begin(),key.end());unordered.push_back(key);for(auto v:t)referenced[v]=true;
    }
    r.normal=r.normals_failed==0;if(!r.normal)throw Rejected("Surviving affected normal reversed or zero");
    std::sort(unordered.begin(),unordered.end());for(std::size_t i=1;i<unordered.size();++i)r.duplicates+=unordered[i]==unordered[i-1];if(r.duplicates)throw Rejected("Duplicate surviving triangle");
    Mesh candidate;std::vector<Vertex> ids(current.num_vertices(),Mesh::null_vertex());std::vector<std::size_t> output_origins;
    for(auto v:current.vertices()) {if(referenced[v.idx()]) {if(map[v.idx()]!=v.idx())throw Rejected("Removed vertex remains referenced");ids[v.idx()]=candidate.add_vertex(current.point(v));output_origins.push_back(origins[v.idx()]);}else if(map[v.idx()]==v.idx())throw Rejected("Unexpected unreferenced retained vertex");}
    auto ap=candidate.add_property_map<Face,bool>("f:atomic-affected",false).first;
    for(std::size_t i=0;i<rows.size();++i) {auto t=rows[i];auto f=candidate.add_face(ids[t[0]],ids[t[1]],ids[t[2]]);if(f==Mesh::null_face())throw Rejected("Quotient faces not valid oriented mesh");ap[f]=affected[i];}
    r.candidate_built=true;r.candidate_vertices=candidate.num_vertices();r.candidate_faces=candidate.num_faces();r.stage="full_quality_and_topology";
    auto q=quality(candidate);r.quality_checked=true;r.bad=q.bad;r.minimum=q.minimum;r.quality=q.bad==0&&q.minimum>=before.minimum;if(!r.quality)throw Rejected("Global necessary quality or minimum failed");
    r.new_topology=topology(candidate);r.topology=r.new_topology.valid&&r.new_topology.components==r.old_topology.components&&r.new_topology.euler==r.old_topology.euler;if(!r.topology)throw Rejected("Full topology/links/components/Euler changed");
    std::vector<bool> output_seen(original.num_vertices(),false);
    for(auto v:candidate.vertices()) {auto id=output_origins[v.idx()];if(output_seen[id]||!same_point_bits(candidate.point(v),original.point(Vertex(id))))throw Rejected("Output origin or coordinate bytes changed");output_seen[id]=true;}
    for(std::size_t i=0;i<fixed.size();++i)if(fixed[i]&&output_seen[i])++r.fixed_retained;r.fixed=r.fixed_retained==r.fixed_count;if(!r.fixed)throw Rejected("Original fixed vertex missing");
    std::sort(exterior.begin(),exterior.end());std::vector<Row> candidate_keys;Chain patch_boundary;
    for(auto t:rows) {Row k=oriented(Row{origins[t[0]],origins[t[1]],origins[t[2]]});candidate_keys.push_back(k);if(!std::binary_search(exterior.begin(),exterior.end(),k)) {++r.patch_faces;chain_add(patch_boundary,k);}}
    std::sort(candidate_keys.begin(),candidate_keys.end());r.exterior=std::includes(candidate_keys.begin(),candidate_keys.end(),exterior.begin(),exterior.end());if(!r.exterior)throw Rejected("Original oriented exterior faces changed");
    r.boundary=before_boundary==after_boundary&&patch_boundary==original_boundary;if(!r.boundary)throw Rejected("Affected or original patch oriented boundary changed");
    r.stage="final_neighbor_policy";
    for(auto e:candidate.edges()) {
      auto h=candidate.halfedge(e),op=candidate.opposite(h);auto f1=candidate.face(h),f2=candidate.face(op);if(!ap[f1]&&!ap[f2])continue;
      const auto &a=candidate.point(candidate.source(h)),&b=candidate.point(candidate.target(h)),&c=candidate.point(candidate.target(candidate.next(h))),&d=candidate.point(candidate.target(candidate.next(op)));
      ++r.neighbor_pairs;int failure=ordinary(a,d,b,c);r.ratio_failed+=failure==1;r.dihedral_failed+=failure==2;
    }
    r.neighbors=!r.ratio_failed&&!r.dihedral_failed;if(!r.neighbors)throw Rejected("Final affected-neighbor ordinary policy failed");
    r.stage="immutable_original_triangle_envelope";CGAL::Polyhedral_envelope<Kernel> envelope(reference,original,0.0625);
    for(auto k:keepers)if(!envelope(current.point(Vertex(k.second))))++r.envelope_failed;
    for(auto t:rows) {Row k=oriented(Row{origins[t[0]],origins[t[1]],origins[t[2]]});if(std::binary_search(exterior.begin(),exterior.end(),k))continue;
      if(!envelope(current.point(Vertex(t[0])),current.point(Vertex(t[1])),current.point(Vertex(t[2]))))++r.envelope_failed;
    }
    r.envelope=r.envelope_failed==0;if(!r.envelope)throw Rejected("Final original-patch triangle envelope failed");
    r.stage="export_after_all_local_guards";write_surface(candidate,out/"candidate.bin");std::ofstream oo(out/"vertex-coordinate-origins.u64",std::ios::binary);for(auto id:output_origins)write_value<std::uint64_t>(oo,id);oo.close();if(!oo)throw std::runtime_error("Origin export failed");
    r.exported=true;r.stage="complete";report(out,r,"local_candidate_only","All declared local guards pass; independent admission gates pending");return 0;
  }catch(const Rejected& e) {try {report(out,r,"rejected_no_candidate",e.what());}catch(const std::exception& r) {std::cerr<<r.what()<<std::endl;return 2;}return 3;
  }catch(const std::exception& e) {try {report(out,r,"error_no_acceptance",e.what());}catch(...) {}std::cerr<<"Atomic refusal: "<<e.what()<<std::endl;return 2;}
}
