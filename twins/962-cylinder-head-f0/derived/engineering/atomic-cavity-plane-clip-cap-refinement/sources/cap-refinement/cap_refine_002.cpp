// Cap-only interior-Steiner hypothesis; never a full-head candidate/admission.
#include "cap_common.hpp"
#include <CGAL/Delaunay_mesher_no_edge_refinement_2.h>
#include <CGAL/Delaunay_mesh_size_criteria_2.h>
#include <CGAL/Delaunay_mesh_face_base_2.h>
#include <CGAL/Delaunay_mesh_vertex_base_2.h>
#include <CGAL/Triangulation_vertex_base_with_info_2.h>
#include <CGAL/Constrained_Delaunay_triangulation_2.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
using Vb=CGAL::Delaunay_mesh_vertex_base_2<Kernel,CGAL::Triangulation_vertex_base_with_info_2<std::size_t,Kernel>>;
using Fb=CGAL::Delaunay_mesh_face_base_2<Kernel>;
using Tds=CGAL::Triangulation_data_structure_2<Vb,Fb>;
using CDT=CGAL::Constrained_Delaunay_triangulation_2<Kernel,Tds,CGAL::No_constraint_intersection_requiring_constructions_tag>;
using Criteria=CGAL::Delaunay_mesh_size_criteria_2<CDT>;
P2 exact_working_point(const Kernel::Point_2& point) {if(!std::isfinite(point.x())||!std::isfinite(point.y()))throw Rejected("Nonfinite working-CDT point");return P2(point.x(),point.y());}
void trace(const std::string& stage,const char* event) {std::cerr<<"stage="<<stage<<" event="<<event<<'\n'<<std::flush;}
constexpr auto NONE=std::numeric_limits<std::uint64_t>::max();
struct Result {
  std::string stage="setup",original_area,mapped_area,embedded_area;
  std::size_t input_vertices=0,input_faces=0,map_rows=0,identity_map_rows=0,nonidentity_map_rows=0,fixed_faces=0,constraints=0;
  std::size_t attempts=0,insertions=0,without_insertion=0,shape_before=0,shape_after=0;
  std::size_t output_vertices=0,output_faces=0,new_interior_points=0,exact_bad=0;
  Quality before,after;std::vector<std::vector<std::size_t>> old_loops,mapped_loops;
  std::map<std::string,bool> guards;bool exported=false;
};
void emit(const fs::path& out,const Result& r,const char* status,const std::string& reason) {
  if(out.empty()||!fs::is_directory(out))return;auto path=out/"report.json";
  if(fs::exists(path))throw std::runtime_error("Existing report preserved");std::ofstream s(path);
  s<<std::setprecision(17)<<"{\"status\":"<<quoted(status)<<",\"stage\":"<<quoted(r.stage)<<",\"reason\":"<<quoted(reason)
   <<",\"input_vertices\":"<<r.input_vertices<<",\"input_faces\":"<<r.input_faces<<",\"map_rows\":"<<r.map_rows
   <<",\"identity_map_rows\":"<<r.identity_map_rows<<",\"nonidentity_map_rows\":"<<r.nonidentity_map_rows
   <<",\"fixed_faces\":"<<r.fixed_faces<<",\"constrained_edges\":"<<r.constraints
   <<",\"shape_aspect_bound\":0.125,\"size_bound\":0,\"refinement_attempts\":"<<r.attempts
   <<",\"requests_with_one_insertion\":"<<r.insertions<<",\"requests_without_insertion\":"<<r.without_insertion
   <<",\"no_insertion_causes_separately_instrumented\":false,\"active_shape_bad_before\":"<<r.shape_before<<",\"active_shape_bad_after\":"<<r.shape_after
   <<",\"output_vertices\":"<<r.output_vertices<<",\"output_faces\":"<<r.output_faces<<",\"new_interior_points\":"<<r.new_interior_points
   <<",\"final_exact_faces_below_2_over_29\":"<<r.exact_bad<<",\"before_quality\":"<<json_quality(r.before)<<",\"after_quality\":"<<json_quality(r.after)
   <<",\"original_cap_area\":"<<quoted(r.original_area)<<",\"mapped_cap_area\":"<<quoted(r.mapped_area)<<",\"embedded_cap_area\":"<<quoted(r.embedded_area)
   <<",\"original_cap_cycles\":[";bool comma=false;for(const auto& l:r.old_loops){if(comma)s<<',';comma=true;list(s,l);}s<<"],\"mapped_cap_cycles\":[";comma=false;
  for(const auto& l:r.mapped_loops){if(comma)s<<',';comma=true;list(s,l);}s<<"],\"guards\":{";comma=false;
  for(const auto& g:r.guards){if(comma)s<<',';comma=true;s<<quoted(g.first)<<':'<<(g.second?"true":"false");}
  s<<"},\"exported\":"<<(r.exported?"true":"false")<<",\"candidate_file_present\":"<<(fs::is_regular_file(out/"cap-candidate.bin")?"true":"false")
   <<",\"interior_Steiner_hypothesis\":true,\"policy_old_coordinate_bits_required\":true,\"new_coordinate_embedding\":\"native working-CDT binary64 XY copied, then exact-dyadic rechecked; no exact circumcentre or nearest-rounding claim\""
   <<",\"working_CDT_kernel\":\"EPICK exact predicates and inexact constructions\",\"proof_kernel\":\"EPECK exact arithmetic on working binary64 coordinates\""
   <<",\"new_point_and_nonfixed_face_provenance_sentinel\":18446744073709551615,\"CGAL_CDT_active_shape_criteria_satisfied\":"<<(r.shape_after==0&&r.guards.count("rounded_embedding_domain_topology_and_quality")?"true":"false")
   <<",\"original_vs_mapped_domain_equality_claimed\":false,\"head_surface_or_solver_admitted\":false,\"manufacturing_authorized\":false}\n";
  s.close();if(!s)throw std::runtime_error("Report write failed");
}
int main(int argc,char** argv) {
  fs::path out;Result r;
  try {
    if(argc!=5)throw std::runtime_error("Usage: cap-refine cap.bin old-to-keeper.u64 fixed-face-ids.u64 fresh-output-directory");
    out=argv[4];if(fs::exists(out)||fs::is_symlink(out)||!fs::create_directory(out)){out.clear();throw std::runtime_error("Fresh output required");}
    r.stage="original_annular_cap";trace(r.stage,"begin");const Mesh original=read_surface(argv[1]);r.input_vertices=original.num_vertices();r.input_faces=original.num_faces();r.before=quality(original);
    std::vector<Row> old;std::map<P2,std::size_t,Exact::Less_xy_2> all_points;
    for(auto v:original.vertices())if(original.point(v).z()!=0||!all_points.emplace(xy(original.point(v)),v.idx()).second)throw Rejected("Distinct original XY points exactly on z0 required");
    FT old_area=0;for(auto f:original.faces()){auto v=vertices(original,f);Row t{v[0].idx(),v[1].idx(),v[2].idx()};old.push_back(t);
      auto sign=cross2(xy(original.point(v[0])),xy(original.point(v[1])),xy(original.point(v[2])));if(sign>=0)throw Rejected("Original cap must wind negative Z");old_area-=sign/2;}
    auto old_complex=complex(old);if(!old_complex.valid||old_complex.components!=1||old_complex.euler!=0||old_complex.loops.size()!=2||old_complex.vertices!=r.input_vertices||old_complex.vertices!=old_complex.boundary.size())throw Rejected("One all-boundary annular cap required");
    if(PMP::does_self_intersect(original))throw Rejected("Original cap self-intersection");
    r.old_loops=old_complex.loops;r.original_area=exact_text(old_area);
    auto read_ids=[&](const fs::path& path){auto bytes=fs::file_size(path);if(bytes%8||bytes/8>r.input_faces)throw std::runtime_error("Bound fixed-face ID rows required");std::ifstream in(path,std::ios::binary);std::vector<std::uint64_t> ids;
      for(std::size_t i=0;i<bytes/8;++i)ids.push_back(read_value<std::uint64_t>(in));if(!std::is_sorted(ids.begin(),ids.end())||std::adjacent_find(ids.begin(),ids.end())!=ids.end())throw std::runtime_error("Sorted unique fixed-face IDs required");if(!ids.empty()&&ids.back()>=r.input_faces)throw Rejected("Fixed-face association outside original cap");return ids;};
    auto fixed_ids=read_ids(argv[3]);r.fixed_faces=fixed_ids.size();std::map<Row,std::uint64_t> frozen;std::set<std::size_t> fixed_vertices;
    for(auto id:fixed_ids){frozen[oriented(old[id])]=id;for(auto v:old[id])fixed_vertices.insert(v);}
    std::vector<std::size_t> map(r.input_vertices);std::iota(map.begin(),map.end(),0);auto bytes=fs::file_size(argv[2]);
    if(bytes%16||bytes/16>r.input_vertices)throw std::runtime_error("Bound old-ID keeper rows required");std::ifstream maps(argv[2],std::ios::binary);std::size_t previous=0;bool first=true;
    for(std::size_t i=0;i<bytes/16;++i){auto a=read_value<std::uint64_t>(maps),b=read_value<std::uint64_t>(maps);if(a>=r.input_vertices||b>=r.input_vertices||(!first&&a<=previous))throw std::runtime_error("Sorted unique source IDs and bounded local keepers required");map[a]=b;r.identity_map_rows+=a==b;r.nonidentity_map_rows+=a!=b;previous=a;first=false;}
    r.map_rows=bytes/16;if(r.map_rows!=r.identity_map_rows+r.nonidentity_map_rows)throw std::runtime_error("Map row count mismatch");for(auto v:map)if(map[v]!=v)throw Rejected("Final local map must be idempotent");std::vector<int> loop_of(r.input_vertices,-1);for(int k=0;k<2;++k)for(auto v:r.old_loops[k])loop_of[v]=k;
    for(std::size_t v=0;v<map.size();++v)if(map[v]!=v&&(map[map[v]]!=map[v]||fixed_vertices.count(v)||fixed_vertices.count(map[v])||loop_of[v]<0||loop_of[v]!=loop_of[map[v]]))throw Rejected("Direct free same-cycle boundary map required");
    r.guards["original_cap_and_fixed_map_association"]=true;trace(r.stage,"end");r.stage="mapped_annulus";trace(r.stage,"begin");std::set<std::size_t> mapped_ids;
    for(const auto& loop:r.old_loops){std::vector<std::size_t> l;for(auto v:loop)if(l.empty()||l.back()!=map[v])l.push_back(map[v]);if(l.size()>1&&l.front()==l.back())l.pop_back();if(l.size()<3)throw Rejected("Mapped cap cycle vanished");for(auto v:l)if(!mapped_ids.insert(v).second)throw Rejected("Repeated mapped cap boundary vertex");r.mapped_loops.push_back(l);}
    std::array<Polygon,2> polygons;for(int k=0;k<2;++k)for(auto v:r.mapped_loops[k])polygons[k].push_back(xy(original.point(Vertex(v))));
    for(const auto& poly:polygons)if(!poly.is_simple()||poly.area()==0)throw Rejected("Simple mapped cycles required");
    for(std::size_t i=0;i<polygons[0].size();++i)for(std::size_t j=0;j<polygons[1].size();++j)if(CGAL::do_intersect(Exact::Segment_2(polygons[0][i],polygons[0][(i+1)%polygons[0].size()]),Exact::Segment_2(polygons[1][j],polygons[1][(j+1)%polygons[1].size()])))throw Rejected("Mapped cap cycles touch or intersect");
    int outer=polygons[0].bounded_side(polygons[1][0])==CGAL::ON_BOUNDED_SIDE?0:1,inner=1-outer;
    if(polygons[outer].bounded_side(polygons[inner][0])!=CGAL::ON_BOUNDED_SIDE||polygons[inner].bounded_side(polygons[outer][0])!=CGAL::ON_UNBOUNDED_SIDE||polygons[outer].area()>=0||polygons[inner].area()<=0)throw Rejected("Mapped annulus nesting/winding differs");
    auto in_domain=[&](const P2& q){return polygons[outer].bounded_side(q)==CGAL::ON_BOUNDED_SIDE&&polygons[inner].bounded_side(q)==CGAL::ON_UNBOUNDED_SIDE;};
    FT area=-polygons[outer].area()-polygons[inner].area();r.mapped_area=exact_text(area);r.guards["mapped_simple_two_loop_annulus"]=true;trace(r.stage,"end");r.stage="fixed_cell_CDT";trace(r.stage,"begin");
    CDT cdt;std::map<std::size_t,CDT::Vertex_handle> handles;std::map<P2,std::size_t,Exact::Less_xy_2> retained;
    for(auto v:mapped_ids){auto q=xy(original.point(Vertex(v)));retained.emplace(q,v);auto point=original.point(Vertex(v));handles[v]=cdt.insert(Kernel::Point_2(point.x(),point.y()));handles[v]->info()=v;}
    std::set<Edge> constraints;Chain boundary;
    for(const auto& loop:r.mapped_loops)for(std::size_t i=0;i<loop.size();++i){auto a=loop[i],b=loop[(i+1)%loop.size()];constraints.insert(std::minmax(a,b));boundary[std::minmax(a,b)]=a<b?1:-1;}
    for(const auto& item:frozen)for(int j=0;j<3;++j){auto a=item.first[j],b=item.first[(j+1)%3];if(!handles.count(a)||!handles.count(b))throw Rejected("Fixed cap source vertex omitted");constraints.insert(std::minmax(a,b));}
    try{for(auto e:constraints)cdt.insert_constraint(handles.at(e.first),handles.at(e.second));}catch(const CDT::Intersection_of_constraints_exception&){throw Rejected("Constructed constraint intersection refused");}
    if(!cdt.is_valid()||cdt.number_of_vertices()!=mapped_ids.size())throw Rejected("Invalid initial CDT or unexpected point");r.constraints=constraints.size();
    auto source_row=[&](CDT::Face_handle f){Row t;for(int j=0;j<3;++j){auto at=retained.find(exact_working_point(f->vertex(j)->point()));t[2-j]=at==retained.end()?NONE:at->second;}return oriented(t);};
    auto centroid=[](CDT::Face_handle f){auto a=exact_working_point(f->vertex(0)->point()),b=exact_working_point(f->vertex(1)->point()),c=exact_working_point(f->vertex(2)->point());return P2((a.x()+b.x()+c.x())/3,(a.y()+b.y()+c.y())/3);};
    auto current_constraints=[&](){std::set<Edge> found;for(auto e=cdt.finite_edges_begin();e!=cdt.finite_edges_end();++e)if(cdt.is_constrained(*e)){auto f=e->first;int j=e->second;auto a=retained.find(exact_working_point(f->vertex(CDT::cw(j))->point())),b=retained.find(exact_working_point(f->vertex(CDT::ccw(j))->point()));if(a==retained.end()||b==retained.end())throw Rejected("New constrained-edge point refused");found.insert(std::minmax(a->second,b->second));}return found;};
    if(current_constraints()!=constraints)throw Rejected("Initial constraints split or altered");std::set<Row> found_fixed;
    for(auto f=cdt.all_faces_begin();f!=cdt.all_faces_end();++f)f->set_in_domain(false);
    for(auto f=cdt.finite_faces_begin();f!=cdt.finite_faces_end();++f){auto key=source_row(f);bool inside=in_domain(centroid(f));if(frozen.count(key)){if(!inside)throw Rejected("Fixed triangle outside mapped annulus");found_fixed.insert(key);}f->set_in_domain(inside&&!frozen.count(key));}
    if(found_fixed.size()!=frozen.size())throw Rejected("Fixed triangles are not exact CDT cells");
    r.guards["explicit_annulus_minus_fixed_marks_and_exact_constraints"]=true;trace(r.stage,"end");r.stage="interior_no_edge_refinement";trace(r.stage,"begin");
    Criteria criteria(0.125,0);auto shape_bad=[&](){std::size_t n=0;for(auto f=cdt.finite_faces_begin();f!=cdt.finite_faces_end();++f)if(f->is_in_domain()){Criteria::Quality q;if(criteria.is_bad_object()(f,q)!=CGAL::Mesh_2::NOT_BAD)++n;}return n;};
    CGAL::Delaunay_mesher_no_edge_refinement_2<CDT,Criteria> mesher(cdt,criteria);mesher.init(true);r.shape_before=shape_bad();
    while(!mesher.is_refinement_done()){auto n=cdt.number_of_vertices();++r.attempts;mesher.try_one_step_refine_mesh();auto after=cdt.number_of_vertices();if(after==n)++r.without_insertion;else if(after==n+1)++r.insertions;else throw std::runtime_error("Unexpected per-step insertion count");}
    r.shape_after=shape_bad();if(r.attempts!=r.insertions+r.without_insertion||cdt.number_of_vertices()!=mapped_ids.size()+r.insertions)throw std::runtime_error("Refinement counter mismatch");
    if(!cdt.is_valid()||current_constraints()!=constraints)throw Rejected("Refined constraints changed");found_fixed.clear();
    for(auto f=cdt.finite_faces_begin();f!=cdt.finite_faces_end();++f){auto key=source_row(f);bool inside=in_domain(centroid(f));if(frozen.count(key)){if(!inside)throw Rejected("Refined fixed triangle outside domain");found_fixed.insert(key);}if(f->is_in_domain()!=(inside&&!frozen.count(key)))throw Rejected("Refined domain marker drift");}
    if(found_fixed.size()!=frozen.size())throw Rejected("Refinement changed a fixed cell");r.guards["no_constrained_edge_split_or_fixed_cell_drift"]=true;trace(r.stage,"end");r.stage="rounded_embedding";trace(r.stage,"begin");
    Mesh candidate;std::vector<std::uint64_t> origins,sources;std::map<std::size_t,std::size_t> old_to_output;std::set<std::array<std::uint64_t,3>> bits;std::set<P2,Exact::Less_xy_2> rounded_xy;
    std::map<P2,CDT::Vertex_handle,Exact::Less_xy_2> ordered;for(auto v=cdt.finite_vertices_begin();v!=cdt.finite_vertices_end();++v)ordered.emplace(exact_working_point(v->point()),v);
    for(auto& item:ordered){auto at=retained.find(item.first);Point q(0,0,0);std::uint64_t id=NONE;
      if(at!=retained.end()){id=at->second;q=original.point(Vertex(id));}else{q=Point(item.second->point().x(),item.second->point().y(),0);++r.new_interior_points;}
      if(!std::isfinite(q.x())||!std::isfinite(q.y())||q.z()!=0)throw Rejected("Nonfinite rounded coordinate");std::array<double,3> xyz{q.x(),q.y(),q.z()};std::array<std::uint64_t,3> key;std::memcpy(key.data(),xyz.data(),sizeof(xyz));if(!bits.insert(key).second||!rounded_xy.insert(xy(q)).second)throw Rejected("Duplicate rounded coordinate bits or XY");
      if(id==NONE){auto x=xy(q);if(!in_domain(x))throw Rejected("Rounded new point is outside or on annulus boundary");for(auto e:constraints)if(Exact::Segment_2(xy(original.point(Vertex(e.first))),xy(original.point(Vertex(e.second)))).has_on(x))throw Rejected("Rounded new point on a constrained edge");}
      auto v=candidate.add_vertex(q);item.second->info()=v.idx();origins.push_back(id);if(id!=NONE)old_to_output[id]=v.idx();}
    if(r.new_interior_points!=r.insertions||old_to_output.size()!=mapped_ids.size())throw Rejected("Inserted or retained point accounting differs");
    for(auto v:candidate.vertices())if(origins[v.idx()]!=NONE&&!same_point_bits(candidate.point(v),original.point(Vertex(origins[v.idx()]))))throw Rejected("Retained coordinate bits differ");
    std::vector<Row> rows;FT embedded=0;std::set<Row> retained_fixed;std::set<Row> unique_faces;
    for(auto f=cdt.finite_faces_begin();f!=cdt.finite_faces_end();++f)if(in_domain(centroid(f))){Row t{f->vertex(0)->info(),f->vertex(2)->info(),f->vertex(1)->info()};auto a=xy(candidate.point(Vertex(t[0]))),b=xy(candidate.point(Vertex(t[1]))),c=xy(candidate.point(Vertex(t[2])));auto det=cross2(a,b,c);
      if(det>=0||!in_domain(P2((a.x()+b.x()+c.x())/3,(a.y()+b.y()+c.y())/3)))throw Rejected("Rounded triangle winding or domain drift");embedded-=det/2;
      FT sum=CGAL::squared_distance(a,b)+CGAL::squared_distance(b,c)+CGAL::squared_distance(c,a);r.exact_bad+=2523*det*det<sum*sum;
      Row key=t;std::sort(key.begin(),key.end());if(!unique_faces.insert(key).second)throw Rejected("Duplicate rounded triangle");Row oldkey{origins[t[0]],origins[t[1]],origins[t[2]]};auto at=frozen.find(oriented(oldkey));if(at!=frozen.end())retained_fixed.insert(at->first);sources.push_back(at==frozen.end()?NONE:at->second);
      if(candidate.add_face(Vertex(t[0]),Vertex(t[1]),Vertex(t[2]))==Mesh::null_face())throw Rejected("Invalid rounded cap face");rows.push_back(t);}
    r.output_vertices=candidate.num_vertices();r.output_faces=candidate.num_faces();r.embedded_area=exact_text(embedded);r.after=quality(candidate);
    Chain expected_boundary;for(const auto& item:boundary){auto a=old_to_output.at(item.first.first),b=old_to_output.at(item.first.second);expected_boundary[std::minmax(a,b)]=(a<b?1:-1)*item.second;}
    auto cc=complex(rows);if(!cc.valid||cc.components!=1||cc.euler!=0||cc.loops.size()!=2||cc.vertices!=candidate.num_vertices()||cc.boundary!=expected_boundary||embedded!=area||retained_fixed.size()!=frozen.size())throw Rejected("Rounded cap topology/domain/area/fixed cells differ");
    if(PMP::does_self_intersect(candidate))throw Rejected("Rounded cap self-intersection");if(r.after.bad||r.exact_bad)throw Rejected("Final cap quality below2/29");
    if(candidate.num_vertices()>2000000||candidate.num_faces()>2000000)throw Rejected("SURF1 codec capacity exceeded");r.guards["rounded_embedding_domain_topology_and_quality"]=true;trace(r.stage,"end");r.stage="export_after_cap_only_guards";trace(r.stage,"begin");
    write_surface(candidate,out/"cap-candidate.bin");std::ofstream oi(out/"vertex-coordinate-origins.u64",std::ios::binary),fi(out/"face-source-ids.u64",std::ios::binary);for(auto id:origins)write_value<std::uint64_t>(oi,id);for(auto id:sources)write_value<std::uint64_t>(fi,id);oi.close();fi.close();if(!oi||!fi)throw std::runtime_error("Provenance export failed");
    r.exported=true;trace(r.stage,"end");r.stage="complete";emit(out,r,"cap_only_local_candidate","Cap-only gates pass; no full-head admission");return 0;
  }catch(const Rejected& e){try{emit(out,r,"rejected_no_candidate",e.what());}catch(...){return 2;}return 3;}
   catch(const std::exception& e){try{emit(out,r,"error_no_acceptance",e.what());}catch(...){}std::cerr<<e.what()<<'\n';return 2;}
}
