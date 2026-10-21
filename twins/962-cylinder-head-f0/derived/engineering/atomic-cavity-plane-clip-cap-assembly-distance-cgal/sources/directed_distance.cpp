// Read-only CGAL 5.6 directed complete-facet query; no mesh or input writes.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/Polygon_mesh_processing/distance.h>
#include <CGAL/version.h>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

using Kernel=CGAL::Exact_predicates_inexact_constructions_kernel;
using Point=Kernel::Point_3;
using Mesh=CGAL::Surface_mesh<Point>;
using Row=std::array<std::uint64_t,3>;
using XYZ=std::array<double,3>;
namespace fs=std::filesystem;
constexpr double GAP=0.0001,EPSILON=GAP/4,BUDGET=0.0625;
struct Raw { std::vector<XYZ> points;std::vector<Row> faces; };
template<class T> T read_value(std::istream& in) {
  T v;if(!in.read(reinterpret_cast<char*>(&v),sizeof(v)))throw std::runtime_error("Incomplete input");return v;
}
void regular(const fs::path& p) {
  if(fs::is_symlink(p)||!fs::is_regular_file(p))throw std::runtime_error("Regular immutable input required");
}
Point point(const XYZ& p) { return Point(p[0],p[1],p[2]); }
bool same_bits(const Point& p,const XYZ& q) {
  XYZ a{p.x(),p.y(),p.z()};return std::memcmp(a.data(),q.data(),sizeof(a))==0;
}
Raw read_surface(const fs::path& path) {
  regular(path);std::ifstream in(path,std::ios::binary);char magic[8];
  if(!in.read(magic,8)||std::memcmp(magic,"962SURF1",8))throw std::runtime_error("Expected 962SURF1");
  auto nv=read_value<std::uint64_t>(in),nf=read_value<std::uint64_t>(in);
  if(!nv||!nf||nv>2000000||nf>2000000||fs::file_size(path)!=24+24*(nv+nf))
    throw std::runtime_error("Invalid indexed surface counts");
  Raw r;r.points.reserve(nv);r.faces.reserve(nf);
  for(std::uint64_t i=0;i<nv;++i) {
    XYZ p{read_value<double>(in),read_value<double>(in),read_value<double>(in)};
    for(double x:p)if(!std::isfinite(x))throw std::runtime_error("Nonfinite coordinate");r.points.push_back(p);
  }
  for(std::uint64_t i=0;i<nf;++i) {
    Row f{read_value<std::uint64_t>(in),read_value<std::uint64_t>(in),read_value<std::uint64_t>(in)};
    if(f[0]>=nv||f[1]>=nv||f[2]>=nv||f[0]==f[1]||f[1]==f[2]||f[2]==f[0]
       ||CGAL::collinear(point(r.points[f[0]]),point(r.points[f[1]]),point(r.points[f[2]])))
      throw std::runtime_error("Invalid or degenerate triangle");r.faces.push_back(f);
  }return r;
}
std::vector<std::uint64_t> read_ids(const fs::path& path,std::size_t nf) {
  regular(path);auto bytes=fs::file_size(path);
  if(!bytes||bytes%8||bytes/8>nf)throw std::runtime_error("Nonempty raw u64 source face IDs required");
  std::ifstream in(path,std::ios::binary);std::vector<std::uint64_t> ids;ids.reserve(bytes/8);
  for(std::size_t i=0;i<bytes/8;++i) {
    auto id=read_value<std::uint64_t>(in);
    if(id>=nf||(!ids.empty()&&id<=ids.back()))throw std::runtime_error("Source IDs must be sorted unique and bounded");
    ids.push_back(id);
  }return ids;
}
Row row(const Mesh& m,Mesh::Face_index f) {
  auto h=m.halfedge(f);return {m.source(h).idx(),m.target(h).idx(),m.target(m.next(h)).idx()};
}
bool cyclic(const Row& a,const Row& b) {
  return a==b||a==Row{b[1],b[2],b[0]}||a==Row{b[2],b[0],b[1]};
}
Mesh build(const Raw& r,const std::vector<std::uint64_t>& ids,bool triangle_union) {
  Mesh m;const auto n=triangle_union?ids.size():r.faces.size();m.reserve(triangle_union?3*n:r.points.size(),3*n,n);
  if(!triangle_union)for(const auto& p:r.points)if(!same_bits(m.point(m.add_vertex(point(p))),p))throw std::runtime_error("Target coordinate bits changed");
  for(std::size_t i=0;i<n;++i) {
    auto old=r.faces[triangle_union?ids[i]:i];Row f=old;
    if(triangle_union)for(int k=0;k<3;++k) {
      auto v=m.add_vertex(point(r.points[old[k]]));f[k]=v.idx();
      if(!same_bits(m.point(v),r.points[old[k]]))throw std::runtime_error("Selected source coordinate bits changed");
    }
    auto face=m.add_face(Mesh::Vertex_index(f[0]),Mesh::Vertex_index(f[1]),Mesh::Vertex_index(f[2]));
    if(face==Mesh::null_face()||!cyclic(row(m,face),f))throw std::runtime_error("Valid oriented triangle mesh required");
  }
  if(m.number_of_faces()!=n||!CGAL::is_triangle_mesh(m)||!CGAL::is_valid_polygon_mesh(m))
    throw std::runtime_error("Invalid constructed triangle graph");return m;
}
template<class T> void append(std::vector<unsigned char>& b,const T& value) {
  const auto* p=reinterpret_cast<const unsigned char*>(&value);b.insert(b.end(),p,p+sizeof(value));
}
std::vector<unsigned char> snapshot(const Mesh& m) {
  std::vector<unsigned char> b;b.reserve(16+32*(m.number_of_vertices()+m.number_of_faces()));
  append(b,std::uint64_t(m.number_of_vertices()));append(b,std::uint64_t(m.number_of_faces()));
  for(auto v:m.vertices()) {append(b,std::uint64_t(v.idx()));XYZ p{m.point(v).x(),m.point(v).y(),m.point(v).z()};for(double x:p)append(b,x);}
  for(auto f:m.faces()) {append(b,std::uint64_t(f.idx()));for(auto v:row(m,f))append(b,v);}return b;
}
bool exact_equal(const std::vector<unsigned char>& a,const std::vector<unsigned char>& b) {
  return a.size()==b.size()&&std::memcmp(a.data(),b.data(),a.size())==0;
}
std::string quote(const std::string& x) {
  std::ostringstream s;s<<'"';for(unsigned char c:x) {
    if(c=='"'||c=='\\')s<<'\\'<<c;else if(c<32)s<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;else s<<c;
  }s<<'"';return s.str();
}
struct Result {
  std::string stage="input";std::size_t sv=0,sf=0,tv=0,tf=0;std::vector<std::uint64_t> ids;
  double scalar=0,lower=0,upper=0;bool observed=false,unchanged=false;
};
void emit(const fs::path& out,const Result& r,const std::string& error) {
  const auto p=out/"report.json";if(fs::exists(p)||fs::is_symlink(p))throw std::runtime_error("Existing report preserved");
  std::ofstream s(p);s<<std::setprecision(17)<<"{\"schema\":\"962-CGAL-directed-bounded-distance/v1\",\"status\":"
   <<quote(error.empty()?"completed_interval":"refused_or_query_failed")<<",\"stage\":"<<quote(r.stage)<<",\"error\":"<<quote(error)
   <<",\"CGAL\":"<<quote(CGAL_VERSION_STR)<<",\"source_full_vertices\":"<<r.sv<<",\"source_full_faces\":"<<r.sf
   <<",\"source_selected_faces\":"<<r.ids.size()<<",\"source_constructed_disjoint_vertices\":"<<3*r.ids.size()
   <<",\"target_full_vertices\":"<<r.tv<<",\"target_full_faces\":"<<r.tf<<",\"selected_original_face_IDs\":[";
  for(std::size_t i=0;i<r.ids.size();++i){if(i)s<<',';s<<r.ids[i];}
  s<<"],\"source_representation\":\"exact oriented triangle union; three copied corners per selected original face\""
   <<",\"target_representation\":\"all input triangles with shared original vertex indices\",\"epsilon_mm\":"<<EPSILON
   <<",\"required_interval_gap_mm\":"<<GAP<<",\"polygon_budget_mm\":"<<BUDGET<<",\"scalar_mm\":";
  if(r.observed)s<<r.scalar;else s<<"null";s<<",\"lower_mm\":";if(r.observed)s<<r.lower;else s<<"null";
  s<<",\"upper_mm\":";if(r.observed)s<<r.upper;else s<<"null";
  s<<",\"actual_interval_gap_mm\":";if(r.observed)s<<r.upper-r.lower;else s<<"null";
  s<<",\"query_completed\":"<<(r.observed&&error.empty()?"true":"false")
   <<",\"polygon_budget_passed\":"<<(r.observed&&error.empty()&&r.upper<=BUDGET?"true":"false")
   <<",\"point_and_oriented_face_snapshots_unchanged\":"<<(r.unchanged?"true":"false")
   <<",\"concurrency\":\"Sequential_tag\",\"match_faces_source\":false,\"match_faces_target\":false,\"normalization\":false"
   <<",\"source_closedness_required\":false,\"complete_target_required\":true,\"roundoff_certificate\":false"
   <<",\"mesh_exported\":false,\"input_files_written\":false,\"two_way_distance_accepted\":false,\"head_or_physics_admitted\":false}\n";
  s.close();if(!s)throw std::runtime_error("Report write failed");
}
int main(int argc,char** argv) {
  fs::path out;Result r;bool owned=false;
  try {
    if(argc!=5)throw std::runtime_error("Usage: directed-distance source.bin complete-target.bin sorted-source-face-ids.u64 fresh-output-directory");
    std::uint16_t endian=1;if(*reinterpret_cast<unsigned char*>(&endian)!=1||sizeof(double)!=8||!std::numeric_limits<double>::is_iec559)
      throw std::runtime_error("Little-endian IEEE binary64 runtime required");
    if(std::string(CGAL_VERSION_STR)!="5.6")throw std::runtime_error("Reviewed CGAL 5.6 required");
    out=argv[4];if(fs::exists(out)||fs::is_symlink(out))throw std::runtime_error("Fresh output required");
    if(!fs::create_directory(out))throw std::runtime_error("Cannot create fresh output");owned=true;
    std::cerr<<"stage read full immutable arrays\n"<<std::flush;
    const auto source=read_surface(argv[1]),target=read_surface(argv[2]);
    r.sv=source.points.size();r.sf=source.faces.size();r.tv=target.points.size();r.tf=target.faces.size();r.ids=read_ids(argv[3],r.sf);
    r.stage="construct";std::cerr<<"stage exact selected triangle union and complete target\n"<<std::flush;
    const Mesh a=build(source,r.ids,true),b=build(target,{},false);const auto before_a=snapshot(a),before_b=snapshot(b);
    r.stage="query";std::cerr<<"stage directed complete-facet query\n"<<std::flush;
    try {r.scalar=CGAL::Polygon_mesh_processing::bounded_error_Hausdorff_distance<CGAL::Sequential_tag>(
      a,b,EPSILON,CGAL::parameters::match_faces(false),CGAL::parameters::match_faces(false));}
    catch(...) {r.unchanged=exact_equal(before_a,snapshot(a))&&exact_equal(before_b,snapshot(b));throw;}
    r.unchanged=exact_equal(before_a,snapshot(a))&&exact_equal(before_b,snapshot(b));
    if(!r.unchanged||!std::isfinite(r.scalar)||r.scalar<0)throw std::runtime_error("Mutation or invalid scalar");
    r.lower=std::max(0.0,std::nextafter(r.scalar-EPSILON,-std::numeric_limits<double>::infinity()));
    r.upper=std::nextafter(r.scalar+EPSILON,std::numeric_limits<double>::infinity());
    if(!std::isfinite(r.lower)||!std::isfinite(r.upper)||r.lower>r.upper||r.upper-r.lower>GAP)
      throw std::runtime_error("Invalid or open required interval");
    r.observed=true;r.stage="completed";emit(out,r,"");std::cerr<<"stage completed interval\n"<<std::flush;return 0;
  }catch(const std::exception& e) {
    std::cerr<<"refused: "<<e.what()<<'\n'<<std::flush;
    if(owned)try{emit(out,r,e.what());}catch(const std::exception& x){std::cerr<<"report failure: "<<x.what()<<'\n';}return 2;
  }
}
