// Exact distances between sampled source points and complete triangle soups.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits_3.h>
#include <CGAL/AABB_triangle_primitive_3.h>
#include <CGAL/AABB_segment_primitive_3.h>
#include <CGAL/squared_distance_3.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Point=K::Point_3;using Segment=K::Segment_3;using Triangle=K::Triangle_3;
using Indices=std::array<std::size_t,3>;
using Triangles=std::vector<Triangle>;using Segments=std::vector<Segment>;
using TTree=CGAL::AABB_tree<CGAL::AABB_traits_3<K,CGAL::AABB_triangle_primitive_3<K,Triangles::const_iterator>>>;
using STree=CGAL::AABB_tree<CGAL::AABB_traits_3<K,CGAL::AABB_segment_primitive_3<K,Segments::const_iterator>>>;
struct Mesh {
  std::vector<Point> vertices;std::vector<Indices> faces;
  explicit Mesh(const char* name) {
    std::ifstream file(name);std::size_t nv=0,nf=0;file>>nv>>nf;
    if(!file || !nv || !nf)throw std::runtime_error("Empty mesh");
    vertices.reserve(nv);faces.resize(nf);
    for(std::size_t i=0;i<nv;++i) {
      double x,y,z;file>>x>>y>>z;
      if(!file || !std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))throw std::runtime_error("Invalid vertex");
      vertices.emplace_back(x,y,z); // exact rational values of the IEEE doubles
    }
    for(auto& f:faces) {file>>f[0]>>f[1]>>f[2];if(!file || f[0]>=nv || f[1]>=nv || f[2]>=nv)throw std::runtime_error("Invalid face");}
  }
};
struct Target {
  Triangles triangles;Segments segments;std::vector<Point> points;
  std::unique_ptr<TTree> triangle_tree;std::unique_ptr<STree> segment_tree;
  explicit Target(const Mesh& mesh) {
    for(const auto& f:mesh.faces) {
      const auto& a=mesh.vertices[f[0]];const auto& b=mesh.vertices[f[1]];const auto& c=mesh.vertices[f[2]];
      if(!CGAL::collinear(a,b,c))triangles.emplace_back(a,b,c);
      else {
        // A collinear triangle is exactly its longest segment, or one point.
        const Point* p=&a;const Point* q=&b;K::FT length=CGAL::squared_distance(a,b);
        for(const auto& pair:std::array<std::pair<const Point*,const Point*>,2>{{{&a,&c},{&b,&c}}}) {
          const auto d=CGAL::squared_distance(*pair.first,*pair.second);
          if(d>length){length=d;p=pair.first;q=pair.second;}
        }
        if(length==0)points.push_back(a);else segments.emplace_back(*p,*q);
      }
    }
    if(!triangles.empty()){triangle_tree=std::make_unique<TTree>(triangles.cbegin(),triangles.cend());triangle_tree->accelerate_distance_queries();}
    if(!segments.empty()){segment_tree=std::make_unique<STree>(segments.cbegin(),segments.cend());segment_tree->accelerate_distance_queries();}
  }
  K::FT distance(const Point& p)const {
    bool have=false;K::FT best=0;
    if(triangle_tree){best=triangle_tree->squared_distance(p);have=true;}
    if(segment_tree){const auto d=segment_tree->squared_distance(p);if(!have || d<best){best=d;have=true;}}
    for(const auto& q:points){const auto d=CGAL::squared_distance(p,q);if(!have || d<best){best=d;have=true;}}
    if(!have)throw std::runtime_error("No target primitives");return best;
  }
  void json(std::ostream& out)const {
    out<<"{\"positive_area_triangles\":"<<triangles.size()<<",\"collinear_triangles_as_segments\":"<<segments.size()<<",\"collapsed_triangles_as_points\":"<<points.size()<<'}';
  }
};
struct Measurement {K::FT maximum=0;Point worst{0,0,0};std::size_t index=0,samples=0;bool centroid=false,pass=true;};
Measurement measure(const Mesh& source,const Target& target,const K::FT& bound2) {
  Measurement result;
  auto query=[&](const Point& p,std::size_t i,bool centroid) {
    const auto d=target.distance(p);++result.samples;if(d>bound2)result.pass=false;
    if(result.samples==1 || d>result.maximum){result.maximum=d;result.worst=p;result.index=i;result.centroid=centroid;}
  };
  for(std::size_t i=0;i<source.vertices.size();++i)query(source.vertices[i],i,false);
  for(std::size_t i=0;i<source.faces.size();++i) {
    const auto& f=source.faces[i];const auto& a=source.vertices[f[0]];const auto& b=source.vertices[f[1]];const auto& c=source.vertices[f[2]];
    query(Point((a.x()+b.x()+c.x())/3,(a.y()+b.y()+c.y())/3,(a.z()+b.z()+c.z())/3),i,true);
  }
  return result;
}
void json(std::ostream& out,const Measurement& m) {
  std::ostringstream exact;exact<<CGAL::exact(m.maximum);
  out<<"{\"maximum_mm\":"<<std::sqrt(CGAL::to_double(m.maximum))<<",\"maximum_distance_squared_exact\":\""<<exact.str()
    <<"\",\"samples\":"<<m.samples<<",\"pass\":"<<m.pass<<",\"worst\":{\"kind\":\""<<(m.centroid?"exact_face_centroids":"vertices")
    <<"\",\"index\":"<<m.index<<",\"point_mm\":["<<CGAL::to_double(m.worst.x())<<','<<CGAL::to_double(m.worst.y())<<','<<CGAL::to_double(m.worst.z())<<"]}}";
}
int main(int argc,char** argv) {
  if(argc!=5){std::cerr<<"Usage: exact_distance INPUT.mesh64 OUTPUT.mesh64 RECEIPT.json MAX_DRIFT_MM\n";return 64;}
  try {
    const double bound=std::stod(argv[4]);if(!std::isfinite(bound)||bound<0)throw std::runtime_error("Invalid bound");
    const K::FT bound2=K::FT(bound)*K::FT(bound);std::ostringstream exact_bound;exact_bound<<CGAL::exact(bound2);
    const auto start=std::chrono::steady_clock::now();Mesh input(argv[1]),output(argv[2]);Target a(input),b(output);
    auto ab=measure(input,b,bound2);auto ba=measure(output,a,bound2);
    std::ofstream receipt(argv[3]);receipt<<std::setprecision(17)<<std::boolalpha
      <<"{\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"CGAL_commit\":\""<<CGAL_STR(CGAL_GIT_HASH)
      <<"\",\"kernel\":\"Epeck; exact original IEEE double coordinates; rational face centroids\",\"input_primitives\":";a.json(receipt);
    receipt<<",\"output_primitives\":";b.json(receipt);receipt<<",\"input_to_output\":";json(receipt,ab);receipt<<",\"output_to_input\":";json(receipt,ba);
    receipt<<",\"shape_drift_limit_mm\":"<<bound<<",\"limit_squared_exact\":\""<<exact_bound.str()<<"\",\"comparison\":\"exact squared_distance <= exact square of the unchanged IEEE bound\""
      <<",\"sampling\":\"All original vertices and exact rational face centroids; not a continuous Hausdorff certificate\",\"pass\":"<<(ab.pass&&ba.pass)
      <<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
    if(!receipt)throw std::runtime_error("Could not write receipt");return ab.pass&&ba.pass?0:2;
  }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 70;}
}
