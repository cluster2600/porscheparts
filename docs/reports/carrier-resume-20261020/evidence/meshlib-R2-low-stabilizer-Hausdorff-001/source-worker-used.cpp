// Complete adaptive Hausdorff screen; exact stored coordinates, CGAL EPECK.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/distance.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/version.h>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<K::Point_3>;
namespace PMP=CGAL::Polygon_mesh_processing;
Mesh read(const char* path){
 std::ifstream in(path);std::size_t nv,nf;in>>nv>>nf;if(!in||!nv||!nf)throw std::runtime_error("Nonempty indexed mesh required");
 Mesh m;std::vector<Mesh::Vertex_index> ids;ids.reserve(nv);
 for(std::size_t i=0;i<nv;++i){double x,y,z;in>>x>>y>>z;if(!in||!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))throw std::runtime_error("Finite full coordinate roster required");ids.push_back(m.add_vertex(K::Point_3(x,y,z)));}
 for(std::size_t i=0;i<nf;++i){std::size_t a,b,c;in>>a>>b>>c;if(!in||a>=nv||b>=nv||c>=nv||m.add_face(ids[a],ids[b],ids[c])==Mesh::null_face())throw std::runtime_error("Full oriented triangle roster required");}
 std::string extra;if(in>>extra)throw std::runtime_error("Trailing input");if(!CGAL::is_closed(m))throw std::runtime_error("Closed carrier surface required");return m;
}
Mesh tetra(double shift){
 Mesh m;auto a=m.add_vertex(K::Point_3(0,0,shift));auto b=m.add_vertex(K::Point_3(1,0,shift));auto c=m.add_vertex(K::Point_3(0,1,shift));auto d=m.add_vertex(K::Point_3(0,0,1+shift));
 m.add_face(a,c,b);m.add_face(a,b,d);m.add_face(a,d,c);m.add_face(b,c,d);return m;
}
Mesh folded_quad(bool diagonal){
 Mesh m;auto a=m.add_vertex(K::Point_3(0,0,0));auto b=m.add_vertex(K::Point_3(1,0,0));auto c=m.add_vertex(K::Point_3(1,1,1));auto d=m.add_vertex(K::Point_3(0,1,0));
 if(diagonal){m.add_face(a,b,c);m.add_face(a,c,d);}else{m.add_face(a,b,d);m.add_face(b,c,d);}return m;
}
double distance(const Mesh&a,const Mesh&b,double error){return PMP::bounded_error_symmetric_Hausdorff_distance<CGAL::Sequential_tag>(a,b,error);}
int main(int argc,char**argv){
 try{
  if(argc!=4)throw std::runtime_error("FIRST SECOND OUTPUT_JSON");
  constexpr double error=.001,limit=.06;
  Mesh control=tetra(0),translated=tetra(.125),qa=folded_quad(true),qb=folded_quad(false);
  const double identity=distance(control,control,error),translation=distance(control,translated,error),interior=distance(qa,qb,error);
  if(identity>error||std::abs(translation-.125)>error||interior<.3||interior>.5)throw std::runtime_error("Analytic or same-vertex interior counterexample refused");
  std::cout<<"controls_passed "<<std::setprecision(17)<<identity<<' '<<translation<<' '<<interior<<std::endl;
  Mesh first=read(argv[1]),second=read(argv[2]);
  const double estimate=distance(first,second,error);if(!std::isfinite(estimate)||estimate<0)throw std::runtime_error("Finite complete distance required");
  const double upper=std::nextafter(estimate+error,std::numeric_limits<double>::infinity());
  const bool pass=upper<=limit;
  std::ofstream out(argv[3]);out<<std::setprecision(17)<<"{\"status\":\""<<(pass?"complete_bounded_Hausdorff_screen_passed":"bounded_Hausdorff_screen_refused")<<"\",\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPECK\",\"first_triangles\":"<<first.number_of_faces()<<",\"second_triangles\":"<<second.number_of_faces()<<",\"symmetric_estimate_mm\":"<<estimate<<",\"CGAL_absolute_error_bound_mm\":"<<error<<",\"outward_rounded_distance_upper_mm\":"<<upper<<",\"fixed_distance_limit_mm\":"<<limit<<",\"full_adaptive_surface_algorithm\":true,\"finite_vertex_samples_only\":false,\"analytic_controls\":{\"identity\":"<<identity<<",\"known_translation_0_125mm\":"<<translation<<",\"same_vertex_different_interior\":"<<interior<<"},\"geometry_adopted\":false}\n";
  if(!out)throw std::runtime_error("Output write failed");std::cout<<"symmetric_upper_mm "<<upper<<std::endl;return pass?0:2;
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 70;}
}
