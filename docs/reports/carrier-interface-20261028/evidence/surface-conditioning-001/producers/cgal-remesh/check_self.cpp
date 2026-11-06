#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/remesh.h>
#include <CGAL/Polygon_mesh_processing/detect_features.h>
#include <CGAL/Polygon_mesh_processing/measure.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/version.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <vector>
#include <cmath>
#include <stdexcept>
#include <chrono>
using K=CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<K::Point_3>;
namespace PMP=CGAL::Polygon_mesh_processing;
void require(bool b,const char*s){if(!b)throw std::runtime_error(s);}
Mesh read_mesh(const char*path){
 std::ifstream in(path);std::size_t nv,nf;in>>nv>>nf;require(bool(in)&&nv>0&&nf>0,"Nonempty input required");Mesh m;std::vector<Mesh::Vertex_index> v;
 for(std::size_t i=0;i<nv;++i){double x,y,z;in>>x>>y>>z;require(bool(in)&&std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z),"Finite coordinates required");v.push_back(m.add_vertex(K::Point_3(x,y,z)));}
 for(std::size_t i=0;i<nf;++i){std::size_t a,b,c;in>>a>>b>>c;require(bool(in)&&a<nv&&b<nv&&c<nv&&a!=b&&a!=c&&b!=c,"Triangle indices invalid");require(!CGAL::collinear(m.point(v[a]),m.point(v[b]),m.point(v[c])),"Zero-area triangle");require(m.add_face(v[a],v[b],v[c])!=Mesh::null_face(),"Face insertion failed");}
 std::string extra;require(!(in>>extra)&&in.eof(),"Trailing input");require(CGAL::is_closed(m)&&CGAL::is_triangle_mesh(m),"Closed triangle surface required");return m;
}
std::size_t remesh(Mesh&m,bool all){
 std::vector<Mesh::Face_index> selected;auto fixed=m.add_property_map<Mesh::Vertex_index,bool>("v:fixed",false).first;
 for(auto f:m.faces()){
  bool inside=true;for(auto v:CGAL::vertices_around_face(m.halfedge(f),m)){auto p=m.point(v);inside=inside&&std::abs(p.x())>66.5&&std::abs(p.x())<90&&std::abs(p.y())>20&&p.z()>-12&&p.z()<14;}
  if(all||inside)selected.push_back(f);else for(auto v:CGAL::vertices_around_face(m.halfedge(f),m))fixed[v]=true;
 }
 require(!selected.empty(),"No selected faces");std::vector<std::pair<Mesh::Vertex_index,K::Point_3>> frozen;for(auto v:m.vertices())if(fixed[v])frozen.emplace_back(v,m.point(v));
 auto constraints=m.add_property_map<Mesh::Edge_index,bool>("e:sharp",false).first;PMP::detect_sharp_edges(m,1.,constraints);
 auto count=selected.size();PMP::isotropic_remeshing(selected,.15,m,CGAL::parameters::number_of_iterations(2).number_of_relaxation_steps(1).vertex_is_constrained_map(fixed).edge_is_constrained_map(constraints).protect_constraints(false).collapse_constraints(true).relax_constraints(false));
 for(const auto&v:frozen)require(!m.is_removed(v.first)&&m.point(v.first)==v.second,"Frozen vertex changed");return count;
}
void write_mesh(Mesh&m,const std::string&path){m.collect_garbage();std::ofstream o(path);o<<std::setprecision(17)<<m.number_of_vertices()<<" "<<m.number_of_faces()<<"\n";for(auto v:m.vertices())o<<m.point(v)<<"\n";for(auto f:m.faces()){auto h=m.halfedge(f);o<<m.source(h).idx()<<" "<<m.target(h).idx()<<" "<<m.target(m.next(h)).idx()<<"\n";}require(bool(o),"Output write failed");}
int main(int argc,char**argv){try{
 require(argc==4,"INPUT CONTROL OUTPUT.json");auto control=read_mesh(argv[2]);remesh(control,true);require(CGAL::is_closed(control)&&!PMP::does_self_intersect(control),"Analytic closed-surface control failed");require(std::abs(PMP::volume(control)-1./6.)<1e-12,"Sharp-feature tetrahedron volume control failed");
 auto m=read_mesh(argv[1]);require(!PMP::does_self_intersect(m),"Input self-intersects");auto start=std::chrono::steady_clock::now();auto before=m.number_of_faces();auto selected=remesh(m,false);require(CGAL::is_closed(m)&&CGAL::is_triangle_mesh(m),"Remeshed topology is invalid");std::string output=argv[3];auto mesh_path=output.substr(0,output.find_last_of('/'))+"/candidate.mesh64";write_mesh(m,mesh_path);bool intersects=PMP::does_self_intersect(m);
 std::ofstream o(output);o<<std::boolalpha<<"{\"status\":\"double_precision_feature_constrained_remesh_trial\",\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPICK binary64\",\"control_passed\":true,\"target_edge_mm\":0.15,\"iterations\":2,\"original_faces\":"<<before<<",\"selected_original_faces\":"<<selected<<",\"output_faces\":"<<m.number_of_faces()<<",\"output_vertices\":"<<m.number_of_vertices()<<",\"self_intersects\":"<<intersects<<",\"outside_region_original_vertices_exact\":true,\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"independent_fidelity_check_pending\":true,\"manufacturing_authorized\":false}\n";return intersects?3:0;
}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 70;}}
