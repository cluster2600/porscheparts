#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_face_graph_triangle_primitive.h>
#include <CGAL/Polyhedral_envelope.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <array>
#include <map>
#include <vector>
#include <iostream>
#include <cmath>
#include <stdexcept>
using K=CGAL::Exact_predicates_inexact_constructions_kernel;
using Point=K::Point_3;using Mesh=CGAL::Surface_mesh<Point>;using Face=Mesh::Face_index;
using Primitive=CGAL::AABB_face_graph_triangle_primitive<Mesh>;
using Tree=CGAL::AABB_tree<CGAL::AABB_traits<K,Primitive>>;
constexpr double epsilon=.0225;
std::array<Point,3> triangle(const Mesh& mesh,Face face){auto h=halfedge(face,mesh);return {mesh.point(source(h,mesh)),mesh.point(target(h,mesh)),mesh.point(target(next(h,mesh),mesh))};}
void require(bool condition){if(!condition)throw std::runtime_error("Self-check failed");}
void self_test(){
 std::vector<Point> p={{0,0,0},{1,0,0},{0,1,0}};std::vector<std::array<int,3>> f={{0,1,2}};
 CGAL::Polyhedral_envelope<K> e(p,f,epsilon);require(e(p[0],p[1],p[2]));require(e(Point(0,0,.005),Point(1,0,.005),Point(0,1,.005)));require(!e(Point(0,0,.2),Point(1,0,.2),Point(0,1,.2)));
 std::vector<Point> q={{0,0,0},{.02,0,0},{0,.02,0},{1,0,0},{1.02,0,0},{1,.02,0},{0,1,0},{.02,1,0},{0,1.02,0}};std::vector<std::array<int,3>> g={{0,1,2},{3,4,5},{6,7,8}};
 CGAL::Polyhedral_envelope<K> holes(q,g,epsilon);require(holes(q[0])&&holes(q[3])&&holes(q[6]));require(!holes(q[0],q[3],q[6]));
 std::cout<<"{\"identical_triangle\":true,\"near_translation\":true,\"far_translation_rejected\":true,\"vertices_only_counterexample_rejected\":true}\n";
}
bool directed(const Mesh& tested,const Mesh& reference,const char* name){
 Tree tree(faces(reference).first,faces(reference).second,reference);tree.build();
 std::map<std::array<int,3>,std::vector<Face>> groups;
 for(Face f:faces(tested)){auto t=triangle(tested,f);std::array<int,3> key;for(int i=0;i<3;i++)key[i]=int(std::floor((CGAL::to_double(t[0][i])+CGAL::to_double(t[1][i])+CGAL::to_double(t[2][i]))/30.));groups[key].push_back(f);}
 std::size_t checked=0;
 for(const auto& group:groups){
  CGAL::Bbox_3 bounds;bool first=true;
  for(Face f:group.second)for(auto p:triangle(tested,f)){if(first){bounds=p.bbox();first=false;}else bounds=bounds+p.bbox();}
  K::Iso_cuboid_3 box(bounds.xmin()-epsilon,bounds.ymin()-epsilon,bounds.zmin()-epsilon,bounds.xmax()+epsilon,bounds.ymax()+epsilon,bounds.zmax()+epsilon);
  std::vector<Face> selected;tree.all_intersected_primitives(box,std::back_inserter(selected));if(selected.empty())return false;
  // A subset envelope is contained in the full reference envelope: success is conservative.
  CGAL::Polyhedral_envelope<K> envelope(selected,reference,epsilon);
  for(Face f:group.second){auto t=triangle(tested,f);if(!envelope(t[0],t[1],t[2])){std::cerr<<name<<" rejected face "<<f<<" after "<<checked<<"\n";return false;}++checked;}
 }
 require(checked==num_faces(tested));std::cerr<<name<<" complete "<<checked<<" triangles, "<<groups.size()<<" tiles\n";return true;
}
int main(int argc,char** argv){
 if(argc==2&&std::string(argv[1])=="--self-test"){self_test();return 0;}if(argc!=3)return 2;
 Mesh a,b;if(!CGAL::IO::read_polygon_mesh(argv[1],a)||!CGAL::IO::read_polygon_mesh(argv[2],b))return 3;
 for(auto* mesh:{&a,&b}){if(num_faces(*mesh)==0||num_faces(*mesh)>4000000||!CGAL::is_closed(*mesh)||!CGAL::is_triangle_mesh(*mesh)||!CGAL::is_valid_polygon_mesh(*mesh)||CGAL::Polygon_mesh_processing::does_self_intersect(*mesh))return 4;for(auto v:vertices(*mesh))for(int i=0;i<3;i++)if(!std::isfinite(CGAL::to_double(mesh->point(v)[i]))||std::abs(CGAL::to_double(mesh->point(v)[i]))>10000)return 4;}
 bool forward=directed(a,b,"source_to_candidate");bool backward=forward&&directed(b,a,"candidate_to_source");
 std::cout<<"{\"source_faces\":"<<num_faces(a)<<",\"candidate_faces\":"<<num_faces(b)<<",\"source_to_candidate_contained\":"<<(forward?"true":"false")<<",\"candidate_to_source_contained\":"<<(backward?"true":"false")<<",\"envelope_bound_native_units\":0.0225,\"reserved_numeric_margin_native_units\":0.0025,\"topology_and_self_intersection_checks_pass\":true,\"complete_containment_pass\":"<<(forward&&backward?"true":"false")<<"}\n";
 return forward&&backward?0:5;
}
