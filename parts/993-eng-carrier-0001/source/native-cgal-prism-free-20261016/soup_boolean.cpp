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
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <vector>

using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Point=K::Point_3;
using Face=std::array<std::size_t,3>;
namespace PMP=CGAL::Polygon_mesh_processing;
constexpr const char* PIN="b4e8c1887ce6a0abeb618634125e5cfcd301ce16";
struct Mesh {std::vector<Point> points;std::vector<Face> faces;};

void assert_closed(const Mesh& mesh) {
  std::map<std::pair<std::size_t,std::size_t>,std::pair<int,int>> edges;
  for(auto t:mesh.faces)for(int j=0;j<3;++j) {
    auto a=t[j],b=t[(j+1)%3];auto key=std::minmax(a,b);
    auto& value=edges[{key.first,key.second}];++value.first;value.second+=a<b?1:-1;
  }
  for(const auto& e:edges)if(e.second.first<2 || e.second.first%2!=0 || e.second.second!=0)
    throw std::runtime_error("Intermediate soup does not form a closed oriented cycle");
}

void assert_clean(const Mesh& mesh) {
  if(mesh.faces.empty())throw std::runtime_error("Unexpected empty intermediate solid");
  for(auto t:mesh.faces)if(CGAL::collinear(mesh.points[t[0]],mesh.points[t[1]],mesh.points[t[2]]))
    throw std::runtime_error("Exactly degenerate intermediate face");
  assert_closed(mesh);
  if(PMP::does_triangle_soup_self_intersect(mesh.points,mesh.faces))
    throw std::runtime_error("Intermediate soup violates binary API self-intersection precondition");
}

Mesh balanced_union(std::vector<Mesh>& solids,std::size_t lo,std::size_t hi,std::size_t& operations) {
  if(hi-lo==1)return std::move(solids[lo]);
  // Deterministic spatial median, longest centroid span. No length tolerance.
  std::array<double,3> lower{INFINITY,INFINITY,INFINITY},upper{-INFINITY,-INFINITY,-INFINITY};
  auto center=[](const Mesh& m,int j) {K::FT s=0;for(const auto& p:m.points)s+=p[j];return CGAL::to_double(s/K::FT(static_cast<int>(m.points.size())));};
  for(std::size_t i=lo;i<hi;++i)for(int j=0;j<3;++j){double c=center(solids[i],j);lower[j]=(std::min)(lower[j],c);upper[j]=(std::max)(upper[j],c);}
  int axis=0;for(int j=1;j<3;++j)if(upper[j]-lower[j]>upper[axis]-lower[axis])axis=j;
  auto mid=lo+(hi-lo)/2;
  std::stable_sort(solids.begin()+lo,solids.begin()+hi,[axis,&center](const Mesh& a,const Mesh& b){return center(a,axis)<center(b,axis);});
  Mesh a=balanced_union(solids,lo,mid,operations),b=balanced_union(solids,mid,hi,operations),out;
  // Leaves are exact positive prisms. Every non-leaf output is checked before
  // it can become a later input to the public binary Boolean API.
  PMP::compute_union(a.points,a.faces,b.points,b.faces,out.points,out.faces,
    CGAL::parameters::concurrency_tag(CGAL::Sequential_tag()));
  assert_clean(out);++operations;
  if(operations%100==0)std::cout<<"validated_binary_unions "<<operations<<std::endl;
  return out;
}

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
  if(argc!=5 && argc!=6 && argc!=7)throw std::runtime_error("Usage: MODE INPUT_A [INPUT_B] OUTPUT RECEIPT or prism_free ROOFS MASK PART OUTPUT RECEIPT");
  std::string mode=argv[1];bool self=mode=="self_union";
  bool prism_free=mode=="prism_free";
  if((self && argc!=5)||(!self && !prism_free && argc!=6)||(prism_free && argc!=7))throw std::runtime_error("Wrong input count");
  std::vector<Point> a,b,points,original_points;
  std::vector<Face> fa,fb,faces,original_faces;
  read_mesh(argv[2],a,fa);
  if(!self)read_mesh(argv[3],b,fb);
  original_points=a;original_faces=fa;
  for(const auto& p:b)original_points.push_back(p);
  for(auto t:fb){for(auto& i:t)i+=a.size();original_faces.push_back(t);}
  const auto start=std::chrono::steady_clock::now();
  auto np=CGAL::parameters::concurrency_tag(CGAL::Sequential_tag());
  std::size_t union_operations=0;
  if(prism_free) {
    Mesh mask{b,fb},part;read_mesh(argv[4],part.points,part.faces);
    assert_clean(mask);assert_clean(part);
    original_points.clear();original_faces.clear();std::vector<Mesh> prisms;
    for(auto roof:fa) {
      Point p=a[roof[0]],q=a[roof[1]],r=a[roof[2]];
      const K::FT cross=(q.x()-p.x())*(r.y()-p.y())-(q.y()-p.y())*(r.x()-p.x());
      if(cross==0)throw std::runtime_error("Degenerate XY roof projection");
      if(cross<0)std::swap(q,r);
      if(p.z()<=0 || q.z()<=0 || r.z()<=0)throw std::runtime_error("Positive common-floor prism requires strictly positive roof heights");
      Mesh m;m.points={Point(p.x(),p.y(),0),Point(q.x(),q.y(),0),Point(r.x(),r.y(),0),p,q,r};
      m.faces={Face{0,2,1},Face{3,4,5},Face{0,1,4},Face{0,4,3},Face{1,2,5},Face{1,5,4},Face{2,0,3},Face{2,3,5}};
      const auto offset=original_points.size();original_points.insert(original_points.end(),m.points.begin(),m.points.end());
      for(auto t:m.faces){for(auto& i:t)i+=offset;original_faces.push_back(t);}
      prisms.push_back(std::move(m));
    }
    Mesh united=balanced_union(prisms,0,prisms.size(),union_operations);std::cout<<"all_prisms_united "<<union_operations<<std::endl;
    Mesh masked;PMP::compute_intersection(united.points,united.faces,mask.points,mask.faces,masked.points,masked.faces,np);assert_clean(masked);
    std::cout<<"masked_prisms_complete "<<masked.faces.size()<<std::endl;
    std::array<double,3> lower{INFINITY,INFINITY,INFINITY},upper{-INFINITY,-INFINITY,-INFINITY};
    for(const auto& p:a)for(int j=0;j<3;++j){lower[j]=(std::min)(lower[j],CGAL::to_double(p[j]));upper[j]=(std::max)(upper[j],CGAL::to_double(p[j]));}
    lower[2]=0; // Every original prism has this exact common floor.
    std::array<double,3> box_lo,box_hi;
    for(int j=0;j<3;++j) {
      double m=(std::max)(std::abs(lower[j]),std::abs(upper[j]));double ulp=std::nextafter(m,INFINITY)-m;
      // Avoid 2^-1074 rationals at zero. These are cutter bounds only, and all
      // original prism vertices are proved strictly within this convex box.
      box_lo[j]=lower[j]==0?-ulp:std::nextafter(lower[j],-INFINITY);
      box_hi[j]=upper[j]==0?ulp:std::nextafter(upper[j],INFINITY);
      if(!(box_lo[j]<lower[j] && box_hi[j]>upper[j]))throw std::runtime_error("Cutter box is not strictly enclosing");
    }
    Mesh box;for(auto xyz:std::vector<std::array<int,3>>{{0,0,0},{1,0,0},{1,1,0},{0,1,0},{0,0,1},{1,0,1},{1,1,1},{0,1,1}})
      box.points.emplace_back(xyz[0]?box_hi[0]:box_lo[0],xyz[1]?box_hi[1]:box_lo[1],xyz[2]?box_hi[2]:box_lo[2]);
    box.faces={Face{0,2,1},Face{0,3,2},Face{4,5,6},Face{4,6,7},Face{0,1,5},Face{0,5,4},Face{1,2,6},Face{1,6,5},Face{2,3,7},Face{2,7,6},Face{3,0,4},Face{3,4,7}};
    Mesh cutter;PMP::compute_intersection(part.points,part.faces,box.points,box.faces,cutter.points,cutter.faces,np);assert_clean(cutter);
    std::cout<<"local_cutter_complete "<<cutter.faces.size()<<std::endl;
    PMP::compute_difference(masked.points,masked.faces,cutter.points,cutter.faces,points,faces,np);
    for(const Mesh* m:{&mask,&part,&box}) {
      auto offset=original_points.size();original_points.insert(original_points.end(),m->points.begin(),m->points.end());
      for(auto t:m->faces){for(auto& i:t)i+=offset;original_faces.push_back(t);}
    }
    std::ofstream box_json(std::string(argv[6])+".bbox.json");box_json<<std::setprecision(17)<<"{\"common_floor_mm\":0,\"all_prisms_strictly_inside\":true,\"strict_bounds_mm\":[["<<box_lo[0]<<','<<box_lo[1]<<','<<box_lo[2]<<"],["<<box_hi[0]<<','<<box_hi[1]<<','<<box_hi[2]<<"]],\"rule\":\"nextafter exterior, except zero uses one ulp of axis maximum absolute bound; cutter only\"}\n";
  }
  else if(self){points=a;faces=fa;PMP::compute_self_union(points,faces,np);}
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
  std::vector<std::size_t> lineage;std::vector<std::vector<std::size_t>> all_parents;std::size_t missing=0,exact_degenerate=0,ambiguous=0;
  K::FT volume6=0;
  for(const auto& t:faces) {
    for(auto i:t)if(i>=points.size())throw std::runtime_error("Invalid output indices");
    const auto& p=points[t[0]];const auto& q=points[t[1]];const auto& r=points[t[2]];
    K::Triangle_3 tr(p,q,r);
    if(tr.is_degenerate()) {
      ++exact_degenerate;++missing;lineage.push_back(std::numeric_limits<std::size_t>::max());all_parents.emplace_back();
      continue; // Never query an AABB tree with a degenerate triangle.
    }
    std::vector<It> hits;tree.all_intersected_primitives(tr,std::back_inserter(hits));
    std::size_t parent=std::numeric_limits<std::size_t>::max();std::vector<std::size_t> matches;
    for(auto it:hits)if(it->has_on(p)&&it->has_on(q)&&it->has_on(r))
      matches.push_back(parent_ids[std::distance(parent_triangles.begin(),it)]);
    std::sort(matches.begin(),matches.end());matches.erase(std::unique(matches.begin(),matches.end()),matches.end());
    if(!matches.empty())parent=matches.front();if(matches.size()>1)++ambiguous;all_parents.push_back(matches);
    if(parent==std::numeric_limits<std::size_t>::max())++missing;
    lineage.push_back(parent);
    volume6+=CGAL::scalar_product(p-CGAL::ORIGIN,CGAL::cross_product(q-CGAL::ORIGIN,r-CGAL::ORIGIN));
  }
  const bool exact_clean=exact_degenerate==0 && !faces.empty() && !PMP::does_triangle_soup_self_intersect(points,faces);
  const char* out_path=argv[prism_free?5:(self?3:4)];const char* receipt_path=argv[prism_free?6:(self?4:5)];
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
  std::ofstream ambiguity(std::string(out_path)+".all_source_faces");
  for(const auto& matches:all_parents){ambiguity<<matches.size();for(auto id:matches)ambiguity<<' '<<id;ambiguity<<'\n';}
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
    <<",\"ambiguous_parent_output_faces\":"<<ambiguous
    <<",\"exact_binary_prism_union_operations\":"<<union_operations
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
