// Separate fixed finishing-datum proposal; EPICK is not exact constructions.
#include "surface_io.hpp"
#include <CGAL/Polygon_mesh_processing/clip.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <map>
#include <limits>
#include <set>

static_assert(sizeof(double)==8 && std::numeric_limits<double>::is_iec559,"IEEE binary64 required");
namespace PMP=CGAL::Polygon_mesh_processing;
using Bits=std::array<std::uint64_t,3>;
Bits point_bits(const Point& p) {
  Bits result;double xyz[3]={p.x(),p.y(),p.z()};
  for(int i=0;i<3;++i)std::memcpy(&result[i],&xyz[i],sizeof(double));
  return result;
}
struct SurfaceAudit {
  std::size_t nv=0,nf=0,cap_faces=0,poor_faces=0;
  double zmin=std::numeric_limits<double>::infinity(),zmax=-zmin,minimum_quality=1;
  long double signed_volume=0,cap_area=0;
};
SurfaceAudit audit(const Mesh& mesh,bool clipped) {
  if(!mesh.number_of_vertices()||!mesh.number_of_faces()
     ||!CGAL::is_closed(mesh)||!CGAL::is_triangle_mesh(mesh)
     ||!CGAL::is_valid_polygon_mesh(mesh))throw std::runtime_error("Invalid closed output/input");
  SurfaceAudit a;std::vector<bool> used(mesh.num_vertices(),false);
  for(auto v:mesh.vertices()) {
    auto p=mesh.point(v);
    if(!std::isfinite(p.x())||!std::isfinite(p.y())||!std::isfinite(p.z())
       ||(clipped&&p.z()<0))throw std::runtime_error("Nonfinite or below-plane coordinate");
    ++a.nv;a.zmin=std::min(a.zmin,p.z());a.zmax=std::max(a.zmax,p.z());
  }
  for(auto f:mesh.faces()) {
    auto v=vertices(mesh,f);auto p=mesh.point(v[0]),q=mesh.point(v[1]),r=mesh.point(v[2]);
    for(auto x:v)used[x.idx()]=true;
    auto normal=CGAL::cross_product(q-p,r-p);double quality_value=triangle_quality(mesh,f);
    if(CGAL::collinear(p,q,r)||!std::isfinite(quality_value)||quality_value<=0)
      throw std::runtime_error("Degenerate or nonfinite triangle");
    ++a.nf;a.poor_faces+=quality_value<2.0/29.0;
    a.minimum_quality=std::min(a.minimum_quality,quality_value);
    a.signed_volume+=(static_cast<long double>(p.x())*(static_cast<long double>(q.y())*r.z()-static_cast<long double>(q.z())*r.y())
       +static_cast<long double>(p.y())*(static_cast<long double>(q.z())*r.x()-static_cast<long double>(q.x())*r.z())
       +static_cast<long double>(p.z())*(static_cast<long double>(q.x())*r.y()-static_cast<long double>(q.y())*r.x()))/6;
    if(clipped&&p.z()==0&&q.z()==0&&r.z()==0) {
      if(!std::isfinite(normal.z())||normal.z()>=0)
        throw std::runtime_error("Non-outward plane cap");
      ++a.cap_faces;a.cap_area-=static_cast<long double>(normal.z())/2;
    }
  }
  for(auto v:mesh.vertices())if(!used[v.idx()])throw std::runtime_error("Unreferenced vertex");
  if(!std::isfinite(a.signed_volume)||a.signed_volume<=0||!std::isfinite(a.cap_area))
    throw std::runtime_error("Nonpositive or nonfinite signed volume/cap area");
  return a;
}
void report_failure(const fs::path& dir,const char* status) {
  std::ofstream out(dir/"report.json");
  out<<"{\"status\":\""<<status<<"\",\"plane\":[0,0,-1,0],\"clip_volume\":true,"
     <<"\"candidate_file_present\":"<<(fs::exists(dir/"candidate.bin")?"true":"false")
     <<",\"point_id_file_present\":"<<(fs::exists(dir/"input-point-ids.u64")?"true":"false")
     <<",\"head_surface_admitted\":false,\"physics_validated\":false,\"manufacturing_authorized\":false}\n";
  out.close();if(!out)throw std::runtime_error("Failure report write failed");
}
int main(int argc,char** argv) {
  fs::path dir;bool owned=false;
  try {
    if(argc!=3)throw std::runtime_error("Usage: plane-clip input.bin fresh-output-directory");
    const fs::path input=argv[1];dir=argv[2];
    if(!fs::is_regular_file(input)||fs::is_symlink(input)||fs::exists(dir)||fs::is_symlink(dir))
      throw std::runtime_error("Regular input and fresh output required");
    const std::uint16_t endian=1;
    if(*reinterpret_cast<const unsigned char*>(&endian)!=1)throw std::runtime_error("Little endian required");
    Mesh mesh=read_surface(input);auto before=audit(mesh,false);
    if(PMP::does_self_intersect(mesh)||!PMP::does_bound_a_volume(mesh))
      throw std::runtime_error("Input does not bound a non-self-intersecting volume");
    std::map<Bits,std::uint64_t> input_ids;
    for(auto v:mesh.vertices())if(!input_ids.emplace(point_bits(mesh.point(v)),v.idx()).second)
      throw std::runtime_error("Ambiguous duplicate input point coordinates");
    if(!fs::create_directory(dir))throw std::runtime_error("Fresh output creation failed");
    owned=true;
    std::cout<<"stage=fixed_plane_volume_clip input_vertices="<<before.nv<<" input_faces="<<before.nf<<std::endl;
    const bool ok=PMP::clip(mesh,Kernel::Plane_3(0,0,-1,0),
      CGAL::parameters::clip_volume(true).use_compact_clipper(true)
        .allow_self_intersections(false).throw_on_self_intersection(true));
    if(!ok){report_failure(dir,"rejected_nonmanifold_boolean_result");return 3;}
    if(mesh.number_of_faces()==0||mesh.number_of_vertices()==0) {
      report_failure(dir,"rejected_empty_result");return 3;
    }
    auto after=audit(mesh,true);
    if(after.nv>2000000||after.nf>2000000)throw std::runtime_error("Output exceeds retained codec count bound");
    if(PMP::does_self_intersect(mesh)||!PMP::does_bound_a_volume(mesh))
      throw std::runtime_error("Output does not bound a non-self-intersecting volume");
    std::vector<std::uint64_t> source_ids;source_ids.reserve(after.nv);
    std::set<std::uint64_t> retained;std::size_t constructed=0;
    for(auto v:mesh.vertices()) {
      auto p=mesh.point(v);auto it=input_ids.find(point_bits(p));
      if(it!=input_ids.end()) {
        if(!retained.insert(it->second).second)throw std::runtime_error("Duplicate retained input coordinate");
        source_ids.push_back(it->second);
      }
      else {
        if(p.z()!=0)throw std::runtime_error("Unexplained off-plane constructed coordinate");
        source_ids.push_back(std::numeric_limits<std::uint64_t>::max());++constructed;
      }
    }
    // IDs describe byte-exact coordinate matches, not CGAL construction history.
    std::ofstream ids(dir/"input-point-ids.u64",std::ios::binary);
    for(auto id:source_ids)write_value<std::uint64_t>(ids,id);
    ids.close();if(!ids)throw std::runtime_error("Point identity output failed");
    write_surface(mesh,dir/"candidate.bin");
    std::ofstream out(dir/"report.json");out<<std::setprecision(17);
    out<<"{\"status\":\"proposal_exported_pending_independent_audits\",\"CGAL\":\""<<CGAL_VERSION_STR<<"\","
       <<"\"kernel\":\"EPICK_inexact_constructions\",\"plane\":[0,0,-1,0],\"clip_volume\":true,"
       <<"\"clip_calls\":1,\"candidate_exported\":true,\"input_vertices\":"<<before.nv<<",\"input_faces\":"<<before.nf
       <<",\"input_signed_volume_mm3\":"<<before.signed_volume<<",\"input_zmin_mm\":"<<before.zmin<<",\"input_zmax_mm\":"<<before.zmax
       <<",\"output_vertices\":"<<after.nv<<",\"output_faces\":"<<after.nf
       <<",\"output_signed_volume_mm3\":"<<after.signed_volume<<",\"output_zmin_mm\":"<<after.zmin<<",\"output_zmax_mm\":"<<after.zmax
       <<",\"plane_cap_faces\":"<<after.cap_faces<<",\"plane_cap_area_mm2\":"<<after.cap_area
       <<",\"exact_input_coordinate_matches\":"<<source_ids.size()-constructed<<",\"constructed_on_plane_coordinates\":"<<constructed
       <<",\"distinct_retained_input_ids\":"<<retained.size()<<",\"unretained_input_coordinate_ids\":"<<before.nv-retained.size()
       <<",\"new_point_id_sentinel\":\"UINT64_MAX\",\"ids_are_coordinate_matches_not_construction_history\":true"
       <<",\"minimum_surface_quality\":"<<after.minimum_quality<<",\"surface_faces_below_2_over_29\":"<<after.poor_faces
       <<",\"surface_quality_screen_passed\":"<<(after.poor_faces==0?"true":"false")
       <<",\"global_independent_topology_intersection_feature_CUB_checks_completed\":false"
       <<",\"head_surface_admitted\":false,\"volume_mesh_admitted\":false,\"physics_validated\":false,\"manufacturing_authorized\":false}\n";
    out.close();if(!out)throw std::runtime_error("Candidate report write failed");
    std::cout<<"stage=proposal_exported output_vertices="<<after.nv<<" output_faces="<<after.nf<<std::endl;
    return 0;
  } catch(const std::exception& error) {
    if(owned)try{report_failure(dir,"rejected_exception_outputs_preserved");}catch(...){}
    std::cerr<<"plane_clip_error: "<<error.what()<<std::endl;return 2;
  }
}
