// Read-only finalization of an already sealed exact checkpoint. No CSG calls.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits_3.h>
#include <CGAL/AABB_triangle_primitive_3.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <type_traits>
#include <utility>
#include <vector>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Point=K::Point_3;
using Face=std::array<std::size_t,3>;
using ET=std::decay_t<decltype(CGAL::exact(std::declval<const K::FT&>()))>;
namespace PMP=CGAL::Polygon_mesh_processing;
constexpr const char* PIN="b4e8c1887ce6a0abeb618634125e5cfcd301ce16";
struct Mesh {std::vector<Point> points;std::vector<Face> faces;};

void read_mesh(const char* path,Mesh& mesh,bool exact) {
  std::ifstream file(path);std::size_t nv=0,nf=0;file>>nv>>nf;
  if(!file||!nv||!nf)throw std::runtime_error("Invalid empty checkpoint/input");
  mesh.points.reserve(nv);
  for(std::size_t i=0;i<nv;++i) {
    if(exact) {ET x,y,z;file>>x>>y>>z;mesh.points.emplace_back(K::FT(x),K::FT(y),K::FT(z));}
    else {double x,y,z;file>>x>>y>>z;if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))throw std::runtime_error("Nonfinite input");mesh.points.emplace_back(x,y,z);}
    if(!file)throw std::runtime_error("Truncated checkpoint vertex");
  }
  mesh.faces.resize(nf);for(auto& t:mesh.faces) {
    file>>t[0]>>t[1]>>t[2];if(!file||t[0]>=nv||t[1]>=nv||t[2]>=nv)throw std::runtime_error("Truncated/invalid checkpoint face");
  }
  std::string extra;if(file>>extra)throw std::runtime_error("Trailing checkpoint data");
}

void balanced_add(std::vector<std::optional<ET>>& bins,ET value) {
  std::size_t level=0;
  while(level<bins.size() && bins[level]){value+=*bins[level];bins[level].reset();++level;}
  if(level==bins.size())bins.emplace_back(std::move(value));else bins[level]=std::move(value);
}
ET finish_sum(const std::vector<std::optional<ET>>& bins) {ET total=0;for(const auto& bin:bins)if(bin)total+=*bin;return total;}

int main(int argc,char** argv) {
 try {
  if(argc==4 && std::string(argv[1])=="--lazy-witness") {
    const std::size_t count=std::stoul(argv[3]);const K::FT term=K::FT(1)/3;
    if(std::string(argv[2])=="naive") {K::FT total=0;for(std::size_t i=0;i<count;++i)total+=term;std::cout<<CGAL::exact(total)<<std::endl;}
    else if(std::string(argv[2])=="balanced") {std::vector<std::optional<ET>> bins;const ET value=CGAL::exact(term);for(std::size_t i=0;i<count;++i)balanced_add(bins,value);std::cout<<finish_sum(bins)<<std::endl;}
    else throw std::runtime_error("Invalid witness mode");
    return 0;
  }
  if(argc!=8)throw std::runtime_error("Usage: ROOFS MASK PART EXACT_CHECKPOINT FLOAT_CHECKPOINT OUTPUT_PREFIX RECEIPT");
  const auto start=std::chrono::steady_clock::now();Mesh roofs,mask,part,exact,rounded;
  read_mesh(argv[1],roofs,false);read_mesh(argv[2],mask,false);read_mesh(argv[3],part,false);
  read_mesh(argv[4],exact,true);read_mesh(argv[5],rounded,false);
  if(exact.points.size()!=rounded.points.size() || exact.faces!=rounded.faces)throw std::runtime_error("Exact/float indexed checkpoint correspondence mismatch");

  std::vector<K::Triangle_3> parents;std::vector<std::size_t> parent_ids;std::size_t next_id=0,input_degenerate=0;
  auto add=[&](const std::vector<Point>& v,const std::vector<Face>& f) {
    for(auto t:f) {K::Triangle_3 tri(v[t[0]],v[t[1]],v[t[2]]);if(tri.is_degenerate())++input_degenerate;else {parents.push_back(tri);parent_ids.push_back(next_id);}++next_id;}
  };
  for(auto t:roofs.faces) {
    Point p=roofs.points[t[0]],q=roofs.points[t[1]],r=roofs.points[t[2]];
    const auto xy=(q.x()-p.x())*(r.y()-p.y())-(q.y()-p.y())*(r.x()-p.x());
    if(xy==0||p.z()<=0||q.z()<=0||r.z()<=0)throw std::runtime_error("Invalid original positive roof");
    if(xy<0)std::swap(q,r);
    std::vector<Point> v{Point(p.x(),p.y(),0),Point(q.x(),q.y(),0),Point(r.x(),r.y(),0),p,q,r};
    std::vector<Face> f{Face{0,2,1},Face{3,4,5},Face{0,1,4},Face{0,4,3},Face{1,2,5},Face{1,5,4},Face{2,0,3},Face{2,3,5}};add(v,f);
  }
  add(mask.points,mask.faces);add(part.points,part.faces);
  std::array<double,3> lo{INFINITY,INFINITY,0},hi{-INFINITY,-INFINITY,-INFINITY};
  for(const auto& p:roofs.points)for(int j=0;j<3;++j){lo[j]=(std::min)(lo[j],CGAL::to_double(p[j]));hi[j]=(std::max)(hi[j],CGAL::to_double(p[j]));}
  lo[2]=0;std::array<double,3> blo,bhi;
  for(int j=0;j<3;++j){double m=(std::max)(std::abs(lo[j]),std::abs(hi[j])),ulp=std::nextafter(m,INFINITY)-m;blo[j]=lo[j]==0?-ulp:std::nextafter(lo[j],-INFINITY);bhi[j]=hi[j]==0?ulp:std::nextafter(hi[j],INFINITY);if(!(blo[j]<lo[j]&&bhi[j]>hi[j]))throw std::runtime_error("Box enclosure mismatch");}
  std::vector<Point> bv;for(auto xyz:std::vector<std::array<int,3>>{{0,0,0},{1,0,0},{1,1,0},{0,1,0},{0,0,1},{1,0,1},{1,1,1},{0,1,1}})bv.emplace_back(xyz[0]?bhi[0]:blo[0],xyz[1]?bhi[1]:blo[1],xyz[2]?bhi[2]:blo[2]);
  std::vector<Face> bf{Face{0,2,1},Face{0,3,2},Face{4,5,6},Face{4,6,7},Face{0,1,5},Face{0,5,4},Face{1,2,6},Face{1,6,5},Face{2,3,7},Face{2,7,6},Face{3,0,4},Face{3,4,7}};add(bv,bf);

  using It=std::vector<K::Triangle_3>::iterator;using Primitive=CGAL::AABB_triangle_primitive_3<K,It>;using Traits=CGAL::AABB_traits_3<K,Primitive>;
  CGAL::AABB_tree<Traits> tree(parents.begin(),parents.end());tree.build();
  std::size_t missing=0,degenerate=0,ambiguous=0,bbox_matches=0;std::vector<std::optional<ET>> volume_bins;
  {
    std::ofstream primary(std::string(argv[6])+".source_faces"),all(std::string(argv[6])+".all_source_faces");std::size_t face_id=0;
    for(auto t:exact.faces) {
      const auto& p=exact.points[t[0]];const auto& q=exact.points[t[1]];const auto& r=exact.points[t[2]];
      std::vector<std::size_t> matches;
      if(CGAL::collinear(p,q,r))++degenerate;
      else {
        const Point centroid((p.x()+q.x()+r.x())/3,(p.y()+q.y()+r.y())/3,(p.z()+q.z()+r.z())/3);std::vector<It> hits;tree.all_intersected_primitives(centroid,std::back_inserter(hits));
        for(auto it:hits)if(it->has_on(p)&&it->has_on(q)&&it->has_on(r))matches.push_back(parent_ids[std::distance(parents.begin(),it)]);
        std::sort(matches.begin(),matches.end());matches.erase(std::unique(matches.begin(),matches.end()),matches.end());
      }
      if(matches.empty())++missing;if(matches.size()>1)++ambiguous;
      for(auto id:matches)if(id>=next_id-12)++bbox_matches;
      primary<<(matches.empty()?std::numeric_limits<std::size_t>::max():matches.front())<<'\n';all<<matches.size();for(auto id:matches)all<<' '<<id;all<<'\n';
      // Force EACH determinant into the exact rational type, then combine
      // rational bins of balanced sizes. Never build a linear lazy += DAG.
      K::FT determinant=CGAL::scalar_product(p-CGAL::ORIGIN,CGAL::cross_product(q-CGAL::ORIGIN,r-CGAL::ORIGIN));
      balanced_add(volume_bins,ET(CGAL::exact(determinant)));
      if(++face_id%10000==0)std::cout<<"finalized_parents "<<face_id<<'/'<<exact.faces.size()<<std::endl;
    }
    if(!primary||!all)throw std::runtime_error("Parent output failure");
  } // Close and flush all parent outputs BEFORE scalar/receipt serialization.
  std::cout<<"all_parents_written"<<std::endl;
  const ET volume=finish_sum(volume_bins)/6;
  std::cout<<"balanced_exact_volume_evaluated"<<std::endl;
  ET maximum_rounding2=0;for(std::size_t i=0;i<exact.points.size();++i){const ET d=CGAL::exact(CGAL::squared_distance(exact.points[i],rounded.points[i]));if(d>maximum_rounding2)maximum_rounding2=d;}
  const bool exact_clean=degenerate==0 && !PMP::does_triangle_soup_self_intersect(exact.points,exact.faces);
  std::size_t rounded_degenerate=0;for(auto t:rounded.faces)if(CGAL::collinear(rounded.points[t[0]],rounded.points[t[1]],rounded.points[t[2]]))++rounded_degenerate;
  const bool rounded_clean=rounded_degenerate==0 && !PMP::does_triangle_soup_self_intersect(rounded.points,rounded.faces);
  const auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  const std::string temporary=std::string(argv[7])+".tmp";
  {
    std::ofstream receipt(temporary);receipt<<std::boolalpha<<std::setprecision(17)
      <<"{\"CGAL_commit\":\""<<PIN<<"\",\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"operation\":\"finalize_existing_exact_checkpoint\",\"operation_completed\":true,\"experimental\":true,\"CSG_recomputed\":false"
      <<",\"input_faces\":"<<next_id<<",\"input_degenerate_faces_excluded_from_parent_AABB\":"<<input_degenerate
      <<",\"output_vertices\":"<<exact.points.size()<<",\"output_faces\":"<<exact.faces.size()
      <<",\"exact_collinear_output_triangles\":"<<degenerate<<",\"exact_output_self_intersection_free\":"<<exact_clean
      <<",\"rounded_collinear_output_triangles\":"<<rounded_degenerate<<",\"rounded_output_self_intersection_free\":"<<rounded_clean
      <<",\"source_face_lineage_complete\":"<<(missing==0)<<",\"unclassified_output_faces\":"<<missing
      <<",\"ambiguous_parent_output_faces\":"<<ambiguous<<",\"bbox_parent_matches\":"<<bbox_matches
      <<",\"exact_signed_volume_mm3\":\""<<volume<<"\",\"signed_volume_mm3\":"<<CGAL::to_double(volume)
      <<",\"volume_accumulation\":\"Each determinant forced to exact rational; online balanced rational reduction; no linear lazy DAG\""
      <<",\"maximum_coordinate_rounding_squared_mm2_exact\":\""<<maximum_rounding2<<"\",\"all_output_coordinates_exactly_double\":"<<(maximum_rounding2==0)
      <<",\"lineage_method\":\"Exact centroid candidate query then all3child vertices in each original triangle; all geometric parents retained\""
      <<",\"kernel\":\"Epeck; sealed exact rational checkpoint; supplied original float checkpoint unchanged\",\"seconds\":"<<seconds<<"}\n";
    if(!receipt)throw std::runtime_error("Native receipt write failure");
  }
  std::filesystem::rename(temporary,argv[7]);
  return exact_clean&&missing==0&&bbox_matches==0 ? 0 : 2;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 70;}
}
