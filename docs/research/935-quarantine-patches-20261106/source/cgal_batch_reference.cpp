#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/triangulate_hole.h>
#include <CGAL/boost/graph/helpers.h>
#include <fstream>
#include <iostream>
#include <stdexcept>
using K=CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<K::Point_3>;
int main(int argc,char** argv){
 try{
  if(argc!=4) throw std::runtime_error("expected input output target_edges");
  Mesh mesh;
  if(!CGAL::IO::read_polygon_mesh(argv[1],mesh)) throw std::runtime_error("input rejected");
  std::ifstream targets(argv[3]);
  if(!targets) throw std::runtime_error("target file unavailable");
  unsigned id,a,b;
  while(targets>>id>>a>>b){
   auto edge=halfedge(Mesh::Vertex_index(a),Mesh::Vertex_index(b),mesh);
   if(!edge.second) throw std::runtime_error("selected edge absent");
   auto h=edge.first;
   if(!is_border(h,mesh)) h=opposite(h,mesh);
   if(!is_border(h,mesh)) throw std::runtime_error("selected edge not a boundary");
   std::vector<Mesh::Face_index> patch;
   CGAL::Polygon_mesh_processing::triangulate_hole(mesh,h,CGAL::parameters::face_output_iterator(std::back_inserter(patch)));
   std::cout<<"{\"contour_id\":"<<id<<",\"added_faces\":"<<patch.size()<<"}"<<std::endl;
  }
  if(!CGAL::IO::write_polygon_mesh(argv[2],mesh,CGAL::parameters::stream_precision(17)))
   throw std::runtime_error("export failed");
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
