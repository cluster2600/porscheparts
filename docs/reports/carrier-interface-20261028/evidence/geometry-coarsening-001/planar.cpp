#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/Polygon_mesh_processing/remesh_planar_patches.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <sys/resource.h>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using M=CGAL::Surface_mesh<K::Point_3>;
int main(int argc,char**argv){
 if(argc!=4)return 2;
 if(std::filesystem::exists(argv[2])||std::filesystem::exists(argv[3]))return 2;
 auto start=std::chrono::steady_clock::now();std::string error;uint64_t nv=0,nf=0,ov=0,of=0;
 try{
  std::ifstream in(argv[1],std::ios::binary);in.read((char*)&nv,8);in.read((char*)&nf,8);
  if(!in||!nv||!nf||nv>20000000||nf>40000000)throw std::runtime_error("Invalid input header");
  M mesh;std::vector<M::Vertex_index> ids;ids.reserve(nv);
  for(uint64_t i=0;i<nv;++i){double p[3];in.read((char*)p,24);if(!in||!std::isfinite(p[0])||!std::isfinite(p[1])||!std::isfinite(p[2]))throw std::runtime_error("Invalid vertex");ids.push_back(mesh.add_vertex(K::Point_3(p[0],p[1],p[2])));}
  for(uint64_t i=0;i<nf;++i){uint64_t f[3];in.read((char*)f,24);if(!in||f[0]>=nv||f[1]>=nv||f[2]>=nv||mesh.add_face(ids[f[0]],ids[f[1]],ids[f[2]])==M::null_face())throw std::runtime_error("Invalid face");}
  if(!CGAL::is_valid_polygon_mesh(mesh)||!CGAL::is_closed(mesh)||!CGAL::is_triangle_mesh(mesh))throw std::runtime_error("Closed triangular input required");
  std::cout<<"INPUT_LOADED "<<nf<<std::endl;
  M result;
  CGAL::Polygon_mesh_processing::remesh_planar_patches(mesh,result,CGAL::parameters::cosine_of_maximum_angle(1.0));
  if(!CGAL::is_valid_polygon_mesh(result)||!CGAL::is_closed(result)||!CGAL::is_triangle_mesh(result))throw std::runtime_error("Closed triangular output required");
  result.collect_garbage();ov=result.number_of_vertices();of=result.number_of_faces();
  std::ofstream out(argv[2],std::ios::binary);out.write((char*)&ov,8);out.write((char*)&of,8);
  for(auto v:result.vertices()){
   auto p=result.point(v);double q[3]={CGAL::to_double(p.x()),CGAL::to_double(p.y()),CGAL::to_double(p.z())};
   if(K::FT(q[0])!=p.x()||K::FT(q[1])!=p.y()||K::FT(q[2])!=p.z())throw std::runtime_error("Inexact output transfer");
   out.write((char*)q,24);
  }
  for(auto f:result.faces()){uint64_t q[3];int n=0;for(auto v:CGAL::vertices_around_face(result.halfedge(f),result)){if(n==3)throw std::runtime_error("Nontriangle");q[n++]=v.idx();}if(n!=3)throw std::runtime_error("Nontriangle");out.write((char*)q,24);}
  if(!out)throw std::runtime_error("Incomplete write");
 }catch(const std::exception&e){error=e.what();}
 struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::ofstream report(argv[3]);report<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"exact_planar_candidate_independent_checks_pending":"exact_planar_refused")<<"\",\"error\":\""<<error<<"\",\"source_vertices\":"<<nv<<",\"source_faces\":"<<nf<<",\"output_vertices\":"<<ov<<",\"output_faces\":"<<of<<",\"cosine_threshold\":1,\"kernel\":\"CGAL5.6 EPECK\",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peak_resident_kib\":"<<usage.ru_maxrss<<",\"independent_fidelity_certified\":false}\n";
 std::cout<<(error.empty()?"GENERATED":"REFUSED")<<" "<<of<<" "<<error<<std::endl;return error.empty()?0:2;
}
