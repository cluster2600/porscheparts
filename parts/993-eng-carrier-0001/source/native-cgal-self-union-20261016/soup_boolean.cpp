// Adapter for the pinned experimental CGAL PR. No upstream algorithm patch.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/triangle_soup_boolean_operations_3.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits_3.h>
#include <CGAL/AABB_triangle_primitive_3.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Point=K::Point_3;
using Face=std::array<std::size_t,3>;
namespace PMP=CGAL::Polygon_mesh_processing;
constexpr const char* PIN="b4e8c1887ce6a0abeb618634125e5cfcd301ce16";

void read_mesh(const char* path,std::vector<Point>& points,std::vector<Face>& faces) {
  std::ifstream file(path);std::size_t nv,nf;file>>nv>>nf;
  if(!file || !nv || !nf)throw std::runtime_error("Invalid empty mesh64");
  for(std::size_t i=0;i<nv;++i) {
    double x,y,z;file>>x>>y>>z;
    if(!file || !std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))
      throw std::runtime_error("Invalid vertex");
    points.emplace_back(x,y,z); // Original IEEE values, not decimal rationals.
  }
  faces.resize(nf);
  for(auto& t:faces) {
    file>>t[0]>>t[1]>>t[2];
    if(!file || t[0]>=nv||t[1]>=nv||t[2]>=nv)throw std::runtime_error("Invalid indices");
  }
  std::string extra;if(file>>extra)throw std::runtime_error("Unexpected trailing input");
}

template<class FT> std::string exact_text(const FT& v) {
  std::ostringstream stream;stream<<CGAL::exact(v);return stream.str();
}

int main(int argc,char** argv) {
 try {
  if(argc!=5 && argc!=6)throw std::runtime_error("Usage: MODE INPUT_A [INPUT_B] OUTPUT RECEIPT");
  std::string mode=argv[1];bool self=mode=="self_union";
  if(self!=(argc==5))throw std::runtime_error("Wrong input count");
  std::vector<Point> a,b,points,original_points;
  std::vector<Face> fa,fb,faces,original_faces;
  read_mesh(argv[2],a,fa);
  if(!self)read_mesh(argv[3],b,fb);
  original_points=a;original_faces=fa;
  for(const auto& p:b)original_points.push_back(p);
  for(auto t:fb){for(auto& i:t)i+=a.size();original_faces.push_back(t);}
  const auto start=std::chrono::steady_clock::now();
  auto np=CGAL::parameters::concurrency_tag(CGAL::Sequential_tag());
  if(self){points=a;faces=fa;PMP::compute_self_union(points,faces,np);}
  else if(mode=="union")PMP::compute_union(a,fa,b,fb,points,faces,np);
  else if(mode=="intersection")PMP::compute_intersection(a,fa,b,fb,points,faces,np);
  else if(mode=="difference")PMP::compute_difference(a,fa,b,fb,points,faces,np);
  else throw std::runtime_error("Unsupported explicit operation");

  // The public API does not forward a visitor. Recover a checkable parent by
  // exact containment of ALL THREE child vertices in one original triangle.
  // Convexity then proves containment of the whole child, independently of
  // upstream face permutations. Degenerate input faces are never AABB primitives.
  std::vector<K::Triangle_3> parent_triangles;std::vector<std::size_t> parent_ids;
  std::size_t input_degenerate=0;
  for(std::size_t i=0;i<original_faces.size();++i) {
    auto t=original_faces[i];K::Triangle_3 tr(original_points[t[0]],original_points[t[1]],original_points[t[2]]);
    if(tr.is_degenerate()){++input_degenerate;continue;}
    parent_triangles.push_back(tr);parent_ids.push_back(i);
  }
  using It=std::vector<K::Triangle_3>::iterator;
  using Primitive=CGAL::AABB_triangle_primitive_3<K,It>;
  using Traits=CGAL::AABB_traits_3<K,Primitive>;
  CGAL::AABB_tree<Traits> tree(parent_triangles.begin(),parent_triangles.end());tree.build();
  std::vector<std::size_t> lineage;std::size_t missing=0,exact_degenerate=0;
  K::FT volume6=0;
  for(const auto& t:faces) {
    for(auto i:t)if(i>=points.size())throw std::runtime_error("Invalid output indices");
    const auto& p=points[t[0]];const auto& q=points[t[1]];const auto& r=points[t[2]];
    K::Triangle_3 tr(p,q,r);
    if(tr.is_degenerate()) {
      ++exact_degenerate;++missing;lineage.push_back(std::numeric_limits<std::size_t>::max());
      continue; // Never query an AABB tree with a degenerate triangle.
    }
    std::vector<It> hits;tree.all_intersected_primitives(tr,std::back_inserter(hits));
    std::size_t parent=std::numeric_limits<std::size_t>::max();
    for(auto it:hits)if(it->has_on(p)&&it->has_on(q)&&it->has_on(r))
      parent=(std::min)(parent,parent_ids[std::distance(parent_triangles.begin(),it)]);
    if(parent==std::numeric_limits<std::size_t>::max())++missing;
    lineage.push_back(parent);
    volume6+=CGAL::scalar_product(p-CGAL::ORIGIN,CGAL::cross_product(q-CGAL::ORIGIN,r-CGAL::ORIGIN));
  }
  const bool exact_clean=exact_degenerate==0 && !faces.empty() && !PMP::does_triangle_soup_self_intersect(points,faces);
  const char* out_path=argv[self?3:4];const char* receipt_path=argv[self?4:5];
  std::ofstream exact(std::string(out_path)+".exact");exact<<points.size()<<' '<<faces.size()<<'\n';
  std::vector<Point> rounded;K::FT maximum_rounding_d2=0;
  for(const auto& p:points) {
    exact<<CGAL::exact(p.x())<<' '<<CGAL::exact(p.y())<<' '<<CGAL::exact(p.z())<<'\n';
    const double x=CGAL::to_double(p.x()),y=CGAL::to_double(p.y()),z=CGAL::to_double(p.z());
    if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))throw std::runtime_error("Nonfinite rounded output");
    rounded.emplace_back(x,y,z);
    maximum_rounding_d2=(std::max)(maximum_rounding_d2,CGAL::squared_distance(p,rounded.back()));
  }
  for(const auto& t:faces)exact<<t[0]<<' '<<t[1]<<' '<<t[2]<<'\n';
  if(!exact)throw std::runtime_error("Exact output write failed");
  std::ofstream output(out_path);output<<points.size()<<' '<<faces.size()<<'\n'<<std::setprecision(17);
  for(const auto& p:rounded)output<<CGAL::to_double(p.x())<<' '<<CGAL::to_double(p.y())<<' '<<CGAL::to_double(p.z())<<'\n';
  for(const auto& t:faces)output<<t[0]<<' '<<t[1]<<' '<<t[2]<<'\n';
  std::ofstream parent_file(std::string(out_path)+".source_faces");for(auto i:lineage)parent_file<<i<<'\n';
  if(!output || !parent_file)throw std::runtime_error("Output write failed");
  std::size_t rounded_degenerate=0;
  for(const auto& t:faces)if(CGAL::collinear(rounded[t[0]],rounded[t[1]],rounded[t[2]]))++rounded_degenerate;
  const bool rounded_clean=rounded_degenerate==0 && !faces.empty() && !PMP::does_triangle_soup_self_intersect(rounded,faces);
  const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  std::ofstream receipt(receipt_path);
  receipt<<std::boolalpha<<std::setprecision(17)
    <<"{\"CGAL_commit\":\""<<PIN<<"\",\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"experimental\":true,"
    <<"\"operation\":\""<<mode<<"\",\"operation_completed\":true,\"public_return_type\":\"void\","
    <<"\"input_faces\":"<<original_faces.size()<<",\"input_A_faces\":"<<fa.size()<<",\"input_B_faces\":"<<fb.size()
    <<",\"input_degenerate_faces_excluded_from_parent_AABB\":"<<input_degenerate
    <<",\"output_vertices\":"<<points.size()<<",\"output_faces\":"<<faces.size()
    <<",\"exact_collinear_output_triangles\":"<<exact_degenerate
    <<",\"exact_output_self_intersection_free\":"<<exact_clean
    <<",\"rounded_collinear_output_triangles\":"<<rounded_degenerate
    <<",\"rounded_output_self_intersection_free\":"<<rounded_clean
    <<",\"source_face_lineage_complete\":"<<(missing==0 && !faces.empty())
    <<",\"unclassified_output_faces\":"<<missing
    <<",\"lineage_method\":\"all three exact child vertices contained in one actual nondegenerate original triangle; AABB candidate search only\""
    <<",\"exact_signed_volume_mm3\":\""<<exact_text(volume6/6)<<"\""
    <<",\"signed_volume_mm3\":"<<CGAL::to_double(volume6/6)
    <<",\"maximum_coordinate_rounding_squared_mm2_exact\":\""<<exact_text(maximum_rounding_d2)<<"\""
    <<",\"all_output_coordinates_exactly_double\":"<<(maximum_rounding_d2==0)
    <<",\"kernel\":\"Epeck from IEEE doubles; exact throughout operation and parent classification; one final conversion\""
    <<",\"seconds\":"<<seconds<<"}\n";
  return exact_clean && missing==0 ? 0 : 2;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 70;}
}
