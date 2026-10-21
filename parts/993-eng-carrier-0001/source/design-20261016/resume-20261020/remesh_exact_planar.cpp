// Exact-kernel planar-patch remeshing of the complete audited IEEE surface.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/remesh_planar_patches.h>
#include <set>
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
  if(argc!=3)throw std::runtime_error("Usage: INPUT_MESH OUTPUT_STEM");
  Mesh input=read(argv[1]),output;
  auto input_patch=input.add_property_map<Mesh::Face_index,std::size_t>("f:patch",0).first;
  auto output_patch=output.add_property_map<Mesh::Face_index,std::size_t>("f:patch",0).first;
  PMP::remesh_planar_patches(input,output,CGAL::parameters::face_patch_map(input_patch),CGAL::parameters::face_patch_map(output_patch));
  if(output.is_empty()||!CGAL::is_closed(output)||!CGAL::is_triangle_mesh(output))throw std::runtime_error("Nonclosed or nontriangular output");
  std::set<K::Point_3> original;
  for(auto v:input.vertices())original.insert(input.point(v));
  std::size_t missing=0;
  for(auto v:output.vertices())if(original.count(output.point(v))==0)++missing;
  save(output,std::string(argv[2]));
  std::ofstream patches(std::string(argv[2])+".patches");
  patches<<input.number_of_faces()<<' '<<output.number_of_faces()<<'\n';
  for(auto f:input.faces())patches<<input_patch[f]<<'\n';
  for(auto f:output.faces())patches<<output_patch[f]<<'\n';
  std::ofstream report(std::string(argv[2])+".json");
  report<<"{\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPECK\",\"input_vertices\":"<<input.number_of_vertices()<<",\"input_faces\":"<<input.number_of_faces()<<",\"output_vertices\":"<<output.number_of_vertices()<<",\"output_faces\":"<<output.number_of_faces()<<",\"output_vertices_absent_from_input\":"<<missing<<",\"independent_geometry_and_surface_audits_pending\":true,\"mechanical_mesh_admitted\":false}\n";
  std::cout<<"planar_retopology "<<input.number_of_faces()<<' '<<output.number_of_faces()<<" new_vertices "<<missing<<std::endl;
  return missing?2:0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 70;}
}
