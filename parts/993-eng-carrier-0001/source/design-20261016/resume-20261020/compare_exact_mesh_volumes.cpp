// Exact-construction CGAL union trial. Inputs are complete saved IEEE meshes.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/corefinement.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/version.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<K::Point_3>;
namespace PMP=CGAL::Polygon_mesh_processing;
Mesh read(const char* path) {
  std::ifstream in(path);size_t nv,nf;in>>nv>>nf;
  if(!in||!nv||!nf)throw std::runtime_error("Empty mesh input");
  Mesh m;std::vector<Mesh::Vertex_index> vertices;
  for(size_t i=0;i<nv;++i){double x,y,z;in>>x>>y>>z;if(!in)throw std::runtime_error("Truncated vertices");vertices.push_back(m.add_vertex(K::Point_3(x,y,z)));}
  for(size_t i=0;i<nf;++i){size_t a,b,c;in>>a>>b>>c;if(!in||a>=nv||b>=nv||c>=nv)throw std::runtime_error("Invalid face");if(m.add_face(vertices[a],vertices[b],vertices[c])==Mesh::null_face())throw std::runtime_error("Input is not an oriented manifold");}
  std::string extra;if(in>>extra)throw std::runtime_error("Trailing input");
  if(!CGAL::is_closed(m))throw std::runtime_error("Open input");return m;
}
void save(const Mesh& m,const std::string& stem){
  std::ofstream exact(stem+".exact"),rounded(stem+".mesh64");
  exact<<m.number_of_vertices()<<' '<<m.number_of_faces()<<'\n';rounded<<m.number_of_vertices()<<' '<<m.number_of_faces()<<'\n'<<std::setprecision(17);
  std::map<Mesh::Vertex_index,size_t> ids;size_t i=0;
  for(auto v:m.vertices()){ids[v]=i++;const auto& p=m.point(v);exact<<CGAL::exact(p.x())<<' '<<CGAL::exact(p.y())<<' '<<CGAL::exact(p.z())<<'\n';rounded<<CGAL::to_double(p.x())<<' '<<CGAL::to_double(p.y())<<' '<<CGAL::to_double(p.z())<<'\n';}
  for(auto f:m.faces()){int n=0;for(auto v:CGAL::vertices_around_face(m.halfedge(f),m)){if(n++){exact<<' ';rounded<<' ';}exact<<ids.at(v);rounded<<ids.at(v);}if(n!=3)throw std::runtime_error("Nontriangular output");exact<<'\n';rounded<<'\n';}
  if(!exact||!rounded)throw std::runtime_error("Output write failed");
}
int main(int argc,char** argv){
 try{
  if(argc!=4)throw std::runtime_error("Usage: FIRST SECOND REPORT");
  Mesh first=read(argv[1]),second=read(argv[2]),a=first,b=second,ab;
  bool ca=PMP::corefine_and_compute_difference(a,b,ab);
  std::cout<<"first_minus_second "<<ca<<' '<<ab.number_of_faces()<<std::endl;
  a=second;b=first;Mesh ba;
  bool cb=PMP::corefine_and_compute_difference(a,b,ba);
  std::cout<<"second_minus_first "<<cb<<' '<<ba.number_of_faces()<<std::endl;
  std::ofstream out(argv[3]);out<<std::boolalpha<<"{\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPECK\",\"first_difference_succeeded\":"<<ca<<",\"first_difference_faces\":"<<ab.number_of_faces()<<",\"second_difference_succeeded\":"<<cb<<",\"second_difference_faces\":"<<ba.number_of_faces()<<",\"both_strict_differences_empty\":"<<(ca&&cb&&ab.is_empty()&&ba.is_empty())<<"}\n";
  return ca&&cb&&ab.is_empty()&&ba.is_empty()?0:2;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 70;}
}
