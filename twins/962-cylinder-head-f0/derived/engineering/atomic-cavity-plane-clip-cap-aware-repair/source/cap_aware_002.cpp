// One declared source-subset quotient plus exact planar CDT; local proposal only.
#include "atomic_policy.hpp"
#include "head_binding.hpp"
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Constrained_Delaunay_triangulation_2.h>
#include <CGAL/Constrained_triangulation_face_base_2.h>
#include <CGAL/Triangulation_vertex_base_with_info_2.h>
#include <CGAL/Triangulation_data_structure_2.h>
#include <CGAL/Polygon_2.h>
using Exact=CGAL::Exact_predicates_exact_constructions_kernel;
using P2=Exact::Point_2;
using FT=Exact::FT;
using Polygon=CGAL::Polygon_2<Exact>;
using Vb=CGAL::Triangulation_vertex_base_with_info_2<std::size_t,Exact>;
using Fb=CGAL::Constrained_triangulation_face_base_2<Exact>;
using Tds=CGAL::Triangulation_data_structure_2<Vb,Fb>;
using CDT=CGAL::Constrained_Delaunay_triangulation_2<Exact,Tds,CGAL::No_constraint_intersection_requiring_constructions_tag>;
constexpr auto NEW_FACE=std::numeric_limits<std::uint64_t>::max();
struct Complex {
  bool valid=false;std::size_t vertices=0,edges=0,faces=0,components=0;long long euler=0;
  Chain boundary;std::vector<std::vector<std::size_t>> loops;
};
Complex complex(const std::vector<Row>& rows) {
  Complex c;c.faces=rows.size();if(rows.empty())return c;
  std::map<Edge,std::vector<std::pair<std::size_t,int>>> edges;
  std::map<std::size_t,std::vector<Edge>> links;UF face_groups(rows.size());
  for(std::size_t i=0;i<rows.size();++i)for(int j=0;j<3;++j) {
    auto a=rows[i][j],b=rows[i][(j+1)%3],d=rows[i][(j+2)%3];
    if(a==b||a==d||b==d)return c;
    edges[std::minmax(a,b)].push_back({i,a<b?1:-1});links[a].push_back(std::minmax(b,d));
  }
  std::map<std::size_t,std::size_t> next;std::map<std::size_t,int> incoming;
  for(const auto& e:edges) {
    if(e.second.size()==2) {if(e.second[0].second+e.second[1].second)return c;face_groups.join(e.second[0].first,e.second[1].first);}
    else if(e.second.size()==1) {
      auto a=e.first.first,b=e.first.second;if(e.second[0].second<0)std::swap(a,b);
      if(!next.emplace(a,b).second||++incoming[b]!=1)return c;
      c.boundary[e.first]=e.second[0].second;
    }else return c;
  }
  if(next.size()!=incoming.size())return c;
  for(const auto& x:next)if(!incoming.count(x.first))return c;
  for(const auto& x:links) {
    std::map<std::size_t,std::vector<std::size_t>> graph;std::set<Edge> unique;
    for(auto e:x.second) {if(!unique.insert(e).second)return c;graph[e.first].push_back(e.second);graph[e.second].push_back(e.first);}
    std::set<std::size_t> unseen;for(const auto& y:graph)unseen.insert(y.first);
    std::vector<std::size_t> pending{*unseen.begin()};unseen.erase(pending[0]);
    while(!pending.empty()) {auto v=pending.back();pending.pop_back();for(auto w:graph[v])if(unseen.erase(w))pending.push_back(w);}
    if(!unseen.empty())return c;std::size_t ends=0;
    for(const auto& y:graph) {ends+=y.second.size()==1;if(y.second.size()!=1&&y.second.size()!=2)return c;}
    if(next.count(x.first)?ends!=2:ends!=0)return c;
  }
  std::set<std::size_t> todo;for(const auto& x:next)todo.insert(x.first);
  while(!todo.empty()) {
    auto first=*todo.begin(),v=first;std::vector<std::size_t> loop;
    do {if(!todo.erase(v))return c;loop.push_back(v);v=next.at(v);}while(v!=first);
    c.loops.push_back(loop);
  }
  for(std::size_t i=0;i<rows.size();++i)c.components+=face_groups.find(i)==i;
  c.vertices=links.size();c.edges=edges.size();c.euler=static_cast<long long>(c.vertices)-static_cast<long long>(c.edges)+static_cast<long long>(c.faces);c.valid=true;return c;
}
double scalar_quality(const Point& a,const Point& b,const Point& c) {
  auto u=b-a,w=c-a;double sum=u.squared_length()+w.squared_length()+(w-u).squared_length();
  return 2*std::sqrt(3.0)*std::sqrt(CGAL::cross_product(u,w).squared_length())/sum;
}
P2 xy(const Point& p) {return P2(p.x(),p.y());}
FT cross2(const P2& a,const P2& b,const P2& c) {return (b.x()-a.x())*(c.y()-a.y())-(b.y()-a.y())*(c.x()-a.x());}
std::string exact_text(const FT& value) {std::ostringstream s;s<<CGAL::exact(value);return s.str();}
std::string quoted(const std::string& value) {
  std::ostringstream s;s<<'"';for(unsigned char c:value) {
    if(c=='"'||c=='\\')s<<'\\'<<c;else if(c<32)s<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;else s<<c;
  }s<<'"';return s.str();
}
template<class T> void list(std::ostream& s,const std::vector<T>& ids) {s<<'[';bool comma=false;for(auto v:ids){if(comma)s<<',';comma=true;s<<v;}s<<']';}
struct Choice {std::size_t first=0,keeper=0;bool selected=false;double score=0;std::vector<std::size_t> members,star;};
struct Result {
  std::string stage="setup",old_area,new_area;std::size_t nv=0,nf=0,targets=0,fixed=0,reference=0,frozen_cap=0,side_dropped=0,cap_faces=0,cap_vertices=0,neighbor_pairs=0;
  std::size_t nv_out=0,nf_out=0,ratio_failed=0,dihedral_failed=0,envelope_failed=0;bool exported=false;
  Quality before,after;Topology old_global,new_global;Complex old_patch,new_patch,old_cap,new_cap;
  std::map<std::string,bool> guards;std::vector<Choice> choices;std::vector<std::size_t> coupled,cap_fixed_ids,poor_ids,reference_ids;std::vector<std::vector<std::size_t>> mapped_loops;
};
void emit(const fs::path& out,const Result& r,const char* status,const std::string& reason) {
  if(out.empty()||!fs::is_directory(out))return;auto path=out/"report.json";if(fs::exists(path))throw std::runtime_error("Existing report preserved");
  std::ofstream s(path);s<<std::setprecision(17)<<"{\"status\":"<<quoted(status)<<",\"stage\":"<<quoted(r.stage)<<",\"reason\":"<<quoted(reason)
   <<",\"input_vertices\":"<<r.nv<<",\"input_faces\":"<<r.nf<<",\"target_edges\":"<<r.targets<<",\"fixed_vertices\":"<<r.fixed<<",\"reference_faces\":"<<r.reference
   <<",\"fixed_cap_faces\":"<<r.frozen_cap<<",\"side_dropped_faces\":"<<r.side_dropped<<",\"cap_faces\":"<<r.cap_faces<<",\"cap_vertices\":"<<r.cap_vertices
   <<",\"output_vertices\":"<<r.nv_out<<",\"output_faces\":"<<r.nf_out<<",\"before_poor_faces\":";
  if(r.before.faces)s<<r.before.bad;else s<<"null";s<<",\"after_poor_faces\":";if(r.after.faces)s<<r.after.bad;else s<<"null";
  s<<",\"before_minimum_quality\":";if(r.before.faces)s<<r.before.minimum;else s<<"null";s<<",\"after_minimum_quality\":";if(r.after.faces)s<<r.after.minimum;else s<<"null";
  s<<",\"global_Euler_before\":";if(r.old_global.valid)s<<r.old_global.euler;else s<<"null";s<<",\"global_Euler_after\":";if(r.new_global.valid)s<<r.new_global.euler;else s<<"null";
  s<<",\"patch_Euler_before\":";if(r.old_patch.valid)s<<r.old_patch.euler;else s<<"null";s<<",\"patch_Euler_after\":";if(r.new_patch.valid)s<<r.new_patch.euler;else s<<"null";
  s<<",\"original_cap_exact_area\":"<<quoted(r.old_area)<<",\"mapped_cap_exact_area\":"<<quoted(r.new_area)<<",\"final_affected_neighbor_pairs\":"<<r.neighbor_pairs
   <<",\"area_ratio_failures\":"<<r.ratio_failed<<",\"dihedral_failures\":"<<r.dihedral_failed<<",\"envelope_failures\":"<<r.envelope_failed<<",\"group_choices\":[";
  bool comma=false;for(const auto& c:r.choices) {if(comma)s<<',';comma=true;s<<"{\"component_minimum\":"<<c.first<<",\"members\":";list(s,c.members);
    s<<",\"selected_keeper\":";if(c.selected)s<<c.keeper;else s<<"null";s<<",\"side_star_minimum_quality\":";if(c.selected)s<<c.score;else s<<"null";s<<",\"side_star_faces\":";list(s,c.star);s<<'}';}
  s<<"],\"native_poor_face_ids\":";list(s,r.poor_ids);s<<",\"native_reference_face_ids\":";list(s,r.reference_ids);
  s<<",\"coupled_side_face_ids\":";list(s,r.coupled);s<<",\"fixed_cap_face_ids\":";list(s,r.cap_fixed_ids);s<<",\"original_cap_cycles\":[";comma=false;
  for(const auto& loop:r.old_cap.loops){if(comma)s<<',';comma=true;list(s,loop);}s<<"],\"mapped_cap_cycles\":[";comma=false;
  for(const auto& loop:r.mapped_loops){if(comma)s<<',';comma=true;list(s,loop);}s<<"],\"guards\":{";comma=false;
  for(const auto& g:r.guards){if(comma)s<<',';comma=true;s<<quoted(g.first)<<':'<<(g.second?"true":"false");}
  s<<"},\"exported\":"<<(r.exported?"true":"false")<<",\"candidate_file_present\":"<<(fs::is_regular_file(out/"candidate.bin")?"true":"false")
   <<",\"independent_maximin_guarantees_simultaneous_feasibility\":false,\"new_cap_face_source_sentinel\":18446744073709551615,\"local_vertex_origins_are_input_coordinate_IDs\":true"
   <<",\"original_vs_mapped_domain_equality_evaluated\":false,\"original_geometric_domain_equality_claimed\":false,\"independent_global_intersection_feature_and_two_sided_distance_pending\":true,\"head_surface_or_solver_admitted\":false,\"manufacturing_authorized\":false}\n";
  s.close();if(!s)throw std::runtime_error("Report write failed");
}
int main(int argc,char** argv) {
  fs::path out;Result r;
  try {
    if(argc!=4)throw std::runtime_error("Usage: cap-aware input.bin targets.u64 fresh-output-directory");
    out=argv[3];if(fs::exists(out)||fs::is_symlink(out)||!fs::create_directory(out)){out.clear();throw std::runtime_error("Fresh output required");}
    const Mesh original=read_surface(argv[1]);r.nv=original.num_vertices();r.nf=original.num_faces();r.stage="immutable_reference";
    r.old_global=topology(original);r.before=quality(original);
    if(!r.old_global.valid||r.old_global.components!=1||r.before.bad==0)throw Rejected("Closed connected poor input required");
    const bool head=r.nv==869355&&r.nf==1739126;
    if(r.old_global.euler!=(head?-208:0))throw Rejected("Bound head or annular fixture Euler differs");
    std::vector<Row> old;std::vector<bool> cap(r.nf,false),seed(r.nv,false),fixed(r.nv,false),inside(r.nf,false),cap_vertex(r.nv,false);std::vector<Face> reference;
    std::vector<Row> cap_rows,patch_rows,exterior;Chain original_boundary;std::map<Row,std::size_t> frozen_cap;
    for(auto v:original.vertices())if(original.point(v).z()<0)throw Rejected("Nonnegative input z required");
    for(auto f:original.faces()) {auto vs=vertices(original,f);Row t{vs[0].idx(),vs[1].idx(),vs[2].idx()};old.push_back(t);
      if(triangle_quality(original,f)<2.0/29.0){r.poor_ids.push_back(f.idx());for(auto v:t)seed[v]=true;}
      cap[f.idx()]=original.point(vs[0]).z()==0&&original.point(vs[1]).z()==0&&original.point(vs[2]).z()==0;
      if(cap[f.idx()]){if(!(cross2(xy(original.point(vs[0])),xy(original.point(vs[1])),xy(original.point(vs[2])))<0))throw Rejected("Original cap must wind negative Z");cap_rows.push_back(t);for(auto v:t)cap_vertex[v]=true;}}
    if(head&&!std::equal(r.poor_ids.begin(),r.poor_ids.end(),head_binding::poor_face_ids.begin(),head_binding::poor_face_ids.end()))throw Rejected("Exact frozen209a poor-face IDs differ");
    r.guards["exact_frozen_head_poor_IDs_or_nonhead_fixture"]=true;
    for(std::size_t i=0;i<old.size();++i) {auto t=old[i];inside[i]=seed[t[0]]||seed[t[1]]||seed[t[2]];
      if(inside[i]){reference.push_back(Face(i));r.reference_ids.push_back(i);patch_rows.push_back(t);chain_add(original_boundary,t);}else {exterior.push_back(oriented(t));for(auto v:t)fixed[v]=true;if(cap[i]){frozen_cap[oriented(t)]=i;r.cap_fixed_ids.push_back(i);}}}
    r.fixed=std::count(fixed.begin(),fixed.end(),true);r.reference=reference.size();r.frozen_cap=frozen_cap.size();r.old_patch=complex(patch_rows);r.old_cap=complex(cap_rows);
    if(!r.old_patch.valid||!r.old_cap.valid||r.old_cap.components!=1||r.old_cap.euler!=0||r.old_cap.loops.size()!=2||r.old_cap.vertices!=r.old_cap.boundary.size())throw Rejected("Manifold patch and all-boundary annular cap required");
    std::vector<int> loop_of(r.nv,-1);for(int k=0;k<2;++k)for(auto v:r.old_cap.loops[k])loop_of[v]=k;
    auto bytes=fs::file_size(argv[2]);if(!bytes||bytes%16||bytes/16>original.num_edges())throw std::runtime_error("Nonempty edge-pair rows required");
    std::ifstream ti(argv[2],std::ios::binary);std::vector<Edge> targets;
    for(std::size_t i=0;i<bytes/16;++i){auto a=read_value<std::uint64_t>(ti),b=read_value<std::uint64_t>(ti);if(a>=b||b>=r.nv)throw std::runtime_error("Ordered bound edge IDs required");targets.emplace_back(a,b);}
    if(!std::is_sorted(targets.begin(),targets.end())||std::adjacent_find(targets.begin(),targets.end())!=targets.end())throw std::runtime_error("Sorted unique targets required");
    r.targets=targets.size();std::set<Edge> wanted(targets.begin(),targets.end()),found;UF uf(r.nv);
    for(auto e:targets)uf.join(e.first,e.second);
    for(auto e:original.edges()){auto h=original.halfedge(e);Edge k=std::minmax(original.source(h).idx(),original.target(h).idx());if(wanted.count(k))found.insert(k);}
    if(found!=wanted)throw Rejected("Every target must be an actual source edge");
    std::map<std::size_t,std::vector<std::size_t>> groups;for(auto e:targets)for(auto v:{e.first,e.second})groups[uf.find(v)].push_back(v);
    std::vector<std::size_t> owner(r.nv,NEW_FACE),map(r.nv);std::iota(map.begin(),map.end(),0);std::map<std::size_t,std::size_t> choice_index;
    for(auto& g:groups){auto& m=g.second;std::sort(m.begin(),m.end());m.erase(std::unique(m.begin(),m.end()),m.end());
      for(auto v:m){if(fixed[v]||!cap_vertex[v]||loop_of[v]!=loop_of[m.front()])throw Rejected("Group must be free on one cap boundary cycle");owner[v]=g.first;}
      choice_index[g.first]=r.choices.size();Choice c;c.first=g.first;c.members=m;r.choices.push_back(c);}
    if(head&&(r.before.bad!=3112||r.reference!=9872||r.fixed!=865429||cap_rows.size()!=3508||r.frozen_cap!=38||r.targets!=2700||groups.size()!=476||r.old_patch.components!=1||r.old_patch.euler!=-4||r.old_patch.loops.size()!=6))throw Rejected("Frozen head reference/group counts differ");
    r.guards["reference_and_exact_target_association"]=true;r.stage="independent_side_star_choices";
    for(std::size_t i=0;i<old.size();++i)if(!cap[i]){std::set<std::size_t> touching;for(auto v:old[i])if(owner[v]!=NEW_FACE)touching.insert(owner[v]);
      if(touching.size()>1)r.coupled.push_back(i);for(auto g:touching)r.choices[choice_index.at(g)].star.push_back(i);}
    for(auto& c:r.choices)for(auto keeper:c.members) {
      bool valid=true;double score=std::numeric_limits<double>::infinity();std::size_t survivors=0;
      for(auto fid:c.star){auto t=old[fid],m=t;for(auto& v:m)if(owner[v]==c.first)v=keeper;if(m[0]==m[1]||m[0]==m[2]||m[1]==m[2])continue;
        auto p=[&](std::size_t v)->const Point&{return original.point(Vertex(v));};auto a=CGAL::cross_product(p(t[1])-p(t[0]),p(t[2])-p(t[0]));auto b=CGAL::cross_product(p(m[1])-p(m[0]),p(m[2])-p(m[0]));
        double q=scalar_quality(p(m[0]),p(m[1]),p(m[2]));if(!(a*b>0)||!std::isfinite(q)||q<=0){valid=false;break;}score=std::min(score,q);++survivors;}
      if(valid&&survivors&&(!c.selected||score>c.score||(score==c.score&&keeper<c.keeper))){c.selected=true;c.keeper=keeper;c.score=score;}}
    for(const auto& c:r.choices){if(!c.selected)throw Rejected("No eligible nonempty side-star choice");for(auto v:c.members)map[v]=c.keeper;}
    r.guards["one_deterministic_independent_keeper_map"]=true;r.stage="mapped_cap_domain";
    std::set<std::size_t> mapped_cap_ids;
    for(const auto& loop:r.old_cap.loops){std::vector<std::size_t> mapped;for(auto v:loop)if(mapped.empty()||mapped.back()!=map[v])mapped.push_back(map[v]);
      if(mapped.size()>1&&mapped.front()==mapped.back())mapped.pop_back();if(mapped.size()<3)throw Rejected("Mapped cap cycle vanished");
      for(auto v:mapped)if(!mapped_cap_ids.insert(v).second)throw Rejected("Mapped cycles repeat or share a vertex");r.mapped_loops.push_back(mapped);}
    std::array<Polygon,2> polygons;for(int k=0;k<2;++k)for(auto v:r.mapped_loops[k])polygons[k].push_back(xy(original.point(Vertex(v))));
    for(const auto& p:polygons)if(!p.is_simple()||p.area()==0)throw Rejected("Mapped cycle must be simple with nonzero exact area");
    for(std::size_t i=0;i<polygons[0].size();++i)for(std::size_t j=0;j<polygons[1].size();++j)
      if(CGAL::do_intersect(Exact::Segment_2(polygons[0][i],polygons[0][(i+1)%polygons[0].size()]),Exact::Segment_2(polygons[1][j],polygons[1][(j+1)%polygons[1].size()])))throw Rejected("Mapped cap cycles touch or cross");
    int outer=polygons[0].bounded_side(polygons[1][0])==CGAL::ON_BOUNDED_SIDE?0:1,inner=1-outer;
    if(polygons[outer].bounded_side(polygons[inner][0])!=CGAL::ON_BOUNDED_SIDE||polygons[inner].bounded_side(polygons[outer][0])!=CGAL::ON_UNBOUNDED_SIDE||polygons[outer].area()>=0||polygons[inner].area()<=0)throw Rejected("Mapped annulus nesting/winding changed");
    FT domain_area=-polygons[outer].area()-polygons[inner].area(),old_area=0;
    for(auto t:cap_rows)old_area-=cross2(xy(original.point(Vertex(t[0]))),xy(original.point(Vertex(t[1]))),xy(original.point(Vertex(t[2]))))/2;
    r.old_area=exact_text(old_area);r.new_area=exact_text(domain_area);r.guards["exact_mapped_two_loop_annulus"]=true;
    r.stage="constrained_cap_triangulation";CDT cdt;std::map<std::size_t,CDT::Vertex_handle> handles;std::map<P2,std::size_t,Exact::Less_xy_2> point_ids;
    for(auto v:mapped_cap_ids){auto p=xy(original.point(Vertex(v)));if(!point_ids.emplace(p,v).second)throw Rejected("Coincident distinct cap source IDs");handles[v]=cdt.insert(p);}
    std::set<Edge> constraints;for(const auto& loop:r.mapped_loops)for(std::size_t i=0;i<loop.size();++i)constraints.insert(std::minmax(loop[i],loop[(i+1)%loop.size()]));
    for(const auto& x:frozen_cap)for(int i=0;i<3;++i){auto a=x.first[i],b=x.first[(i+1)%3];if(!handles.count(a)||!handles.count(b))throw Rejected("Fixed cap vertex omitted");constraints.insert(std::minmax(a,b));}
    try {for(auto e:constraints)cdt.insert_constraint(handles.at(e.first),handles.at(e.second));}
    catch(const CDT::Intersection_of_constraints_exception&){throw Rejected("Constraint intersection requires a constructed point");}
    if(!cdt.is_valid()||cdt.number_of_vertices()!=mapped_cap_ids.size())throw Rejected("Invalid CDT or inserted point");
    for(auto v=cdt.finite_vertices_begin();v!=cdt.finite_vertices_end();++v){auto at=point_ids.find(v->point());if(at==point_ids.end())throw Rejected("Unexpected CDT coordinate");v->info()=at->second;}
    std::vector<Row> rows;std::vector<bool> affected;std::vector<std::uint64_t> sources;
    for(std::size_t i=0;i<old.size();++i)if(!cap[i]){Row t=old[i],m{map[t[0]],map[t[1]],map[t[2]]};bool a=owner[t[0]]!=NEW_FACE||owner[t[1]]!=NEW_FACE||owner[t[2]]!=NEW_FACE;
      if(m[0]==m[1]||m[0]==m[2]||m[1]==m[2]){++r.side_dropped;continue;}
      const auto &p0=original.point(Vertex(m[0])),&p1=original.point(Vertex(m[1])),&p2=original.point(Vertex(m[2]));auto n=CGAL::cross_product(p1-p0,p2-p0);auto on=CGAL::cross_product(original.point(Vertex(t[1]))-original.point(Vertex(t[0])),original.point(Vertex(t[2]))-original.point(Vertex(t[0])));
      if(!std::isfinite(n.squared_length())||n.squared_length()<=0||a&&!(on*n>0))throw Rejected("Combined side map degenerates or reverses a face");
      rows.push_back(m);affected.push_back(a);sources.push_back(i);}
    std::vector<Row> new_cap;FT area=0;std::set<Row> found_fixed;
    for(auto f=cdt.finite_faces_begin();f!=cdt.finite_faces_end();++f){P2 a=f->vertex(0)->point(),b=f->vertex(1)->point(),d=f->vertex(2)->point();P2 center((a.x()+b.x()+d.x())/3,(a.y()+b.y()+d.y())/3);
      if(polygons[outer].bounded_side(center)!=CGAL::ON_BOUNDED_SIDE||polygons[inner].bounded_side(center)!=CGAL::ON_UNBOUNDED_SIDE)continue;
      Row t{f->vertex(0)->info(),f->vertex(2)->info(),f->vertex(1)->info()};auto sign=cross2(xy(original.point(Vertex(t[0]))),xy(original.point(Vertex(t[1]))),xy(original.point(Vertex(t[2]))));
      if(sign>=0)throw Rejected("New cap winding is not negative Z");area-=sign/2;Row key=oriented(t);auto frozen=frozen_cap.find(key);if(frozen!=frozen_cap.end())found_fixed.insert(key);
      rows.push_back(t);new_cap.push_back(t);affected.push_back(frozen==frozen_cap.end());sources.push_back(frozen==frozen_cap.end()?NEW_FACE:frozen->second);}
    r.new_cap=complex(new_cap);r.cap_faces=new_cap.size();r.cap_vertices=r.new_cap.vertices;
    Chain mapped_boundary;for(const auto& loop:r.mapped_loops)for(std::size_t i=0;i<loop.size();++i){auto a=loop[i],b=loop[(i+1)%loop.size()];mapped_boundary[std::minmax(a,b)]=a<b?1:-1;}
    if(area!=domain_area||found_fixed.size()!=frozen_cap.size()||!r.new_cap.valid||r.new_cap.components!=1||r.new_cap.euler!=0||r.new_cap.loops.size()!=2||r.new_cap.boundary!=mapped_boundary||r.new_cap.vertices!=mapped_cap_ids.size())throw Rejected("Mapped cap coverage/topology/fixed triangles differ");
    r.guards["cap_domain_coverage_plane_winding_fixed_faces_no_new_points"]=true;r.stage="combined_full_quality_and_topology";
    std::vector<Row> unordered;std::vector<bool> referenced(r.nv,false);for(auto t:rows){Row key=t;std::sort(key.begin(),key.end());unordered.push_back(key);for(auto v:t)referenced[v]=true;}
    std::sort(unordered.begin(),unordered.end());if(std::adjacent_find(unordered.begin(),unordered.end())!=unordered.end())throw Rejected("Duplicate combined triangle");
    Mesh candidate;std::vector<Vertex> ids(r.nv,Mesh::null_vertex());std::vector<std::uint64_t> origins;
    for(auto v:original.vertices()){if(referenced[v.idx()]){if(map[v.idx()]!=v.idx())throw Rejected("Removed vertex remains referenced");ids[v.idx()]=candidate.add_vertex(original.point(v));origins.push_back(v.idx());}else if(map[v.idx()]==v.idx())throw Rejected("Unexpected unreferenced retained vertex");}
    auto ap=candidate.add_property_map<Face,bool>("f:cap-aware-affected",false).first;
    for(std::size_t i=0;i<rows.size();++i){auto t=rows[i];auto f=candidate.add_face(ids[t[0]],ids[t[1]],ids[t[2]]);if(f==Mesh::null_face())throw Rejected("Invalid oriented combined mesh");ap[f]=affected[i];}
    r.after=quality(candidate);r.nv_out=candidate.num_vertices();r.nf_out=candidate.num_faces();
    if(!(r.before.bad>0&&r.after.bad==0&&r.after.minimum>=r.before.minimum))throw Rejected("Combined global quality objective failed");r.guards["combined_global_quality"]=true;
    r.new_global=topology(candidate);if(!r.new_global.valid||r.new_global.components!=r.old_global.components||r.new_global.euler!=r.old_global.euler)throw Rejected("Global topology/links/components/Euler changed");
    for(auto v:candidate.vertices())if(!same_point_bits(candidate.point(v),original.point(Vertex(origins[v.idx()])))||candidate.point(v).z()<0)throw Rejected("Retained coordinate bits or nonnegative z changed");
    for(std::size_t i=0;i<r.nv;++i)if(fixed[i]&&!referenced[i])throw Rejected("Fixed exterior vertex missing");
    std::sort(exterior.begin(),exterior.end());std::vector<Row> keys,new_patch;
    for(auto t:rows){auto key=oriented(t);keys.push_back(key);if(!std::binary_search(exterior.begin(),exterior.end(),key))new_patch.push_back(t);}
    std::sort(keys.begin(),keys.end());if(!std::includes(keys.begin(),keys.end(),exterior.begin(),exterior.end()))throw Rejected("Exact oriented exterior face missing");
    r.new_patch=complex(new_patch);if(!r.new_patch.valid||r.new_patch.components!=r.old_patch.components||r.new_patch.euler!=r.old_patch.euler||r.new_patch.loops.size()!=r.old_patch.loops.size()||r.new_patch.boundary!=original_boundary)throw Rejected("Patch links/Euler/oriented boundaries changed");
    r.guards["combined_topology_fixed_exterior_oriented_patch_boundary"]=true;r.stage="final_neighbor_and_envelope";
    for(auto e:candidate.edges()){auto h=candidate.halfedge(e),op=candidate.opposite(h);auto f1=candidate.face(h),f2=candidate.face(op);if(!ap[f1]&&!ap[f2])continue;
      const auto &a=candidate.point(candidate.source(h)),&b=candidate.point(candidate.target(h)),&c=candidate.point(candidate.target(candidate.next(h))),&d=candidate.point(candidate.target(candidate.next(op)));
      ++r.neighbor_pairs;auto fail=ordinary(a,d,b,c);r.ratio_failed+=fail==1;r.dihedral_failed+=fail==2;}
    if(r.ratio_failed||r.dihedral_failed)throw Rejected("Final affected-neighbor ordinary policy failed");r.guards["final_affected_neighbor_policy"]=true;
    CGAL::Polyhedral_envelope<Kernel> envelope(reference,original,0.0625);
    for(const auto& c:r.choices)if(!envelope(original.point(Vertex(c.keeper))))++r.envelope_failed;
    for(auto t:rows)if(!std::binary_search(exterior.begin(),exterior.end(),oriented(t)))if(!envelope(original.point(Vertex(t[0])),original.point(Vertex(t[1])),original.point(Vertex(t[2]))))++r.envelope_failed;
    if(r.envelope_failed)throw Rejected("Changed full triangle exceeds immutable local envelope");r.guards["immutable_local_full_triangle_envelope"]=true;r.stage="export_after_all_local_guards";
    write_surface(candidate,out/"candidate.bin");std::ofstream oi(out/"vertex-coordinate-origins.u64",std::ios::binary),fi(out/"face-source-ids.u64",std::ios::binary);
    for(auto id:origins)write_value<std::uint64_t>(oi,id);for(auto id:sources)write_value<std::uint64_t>(fi,id);oi.close();fi.close();if(!oi||!fi)throw std::runtime_error("Provenance export failed");
    r.exported=true;r.stage="complete";emit(out,r,"local_candidate_only","Combined local guards pass; independent admission gates pending");return 0;
  }catch(const Rejected& e){try{emit(out,r,"rejected_no_candidate",e.what());}catch(...){return 2;}return 3;}
   catch(const std::exception& e){try{emit(out,r,"error_no_acceptance",e.what());}catch(...){}std::cerr<<e.what()<<'\n';return 2;}
}
