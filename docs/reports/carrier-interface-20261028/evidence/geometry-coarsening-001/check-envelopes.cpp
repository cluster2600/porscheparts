#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polyhedral_envelope.h>
#include <fstream>
#include <vector>
#include <iostream>
#include <iomanip>
#include <chrono>
#include <sys/resource.h>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using M=CGAL::Surface_mesh<K::Point_3>;
M read(const char*path){
  std::ifstream in(path,std::ios::binary);uint64_t nv=0,nf=0;in.read((char*)&nv,8);in.read((char*)&nf,8);
  if(!in||nv>20000000||nf>40000000)throw std::runtime_error("Invalid header");
  M m;std::vector<M::Vertex_index>v;
  for(uint64_t i=0;i<nv;++i){double p[3];in.read((char*)p,24);if(!in)throw std::runtime_error("Missing point");v.push_back(m.add_vertex(K::Point_3(p[0],p[1],p[2])));}
  for(uint64_t i=0;i<nf;++i){uint64_t f[3];in.read((char*)f,24);if(!in||f[0]>=nv||f[1]>=nv||f[2]>=nv||m.add_face(v[f[0]],v[f[1]],v[f[2]])==M::null_face())throw std::runtime_error("Invalid face");}
  return m;
}
int main(int argc,char**argv){
  if(argc!=5)return 2;
  std::string error;bool forward=false,reverse=false;uint64_t nf=0,ng=0;double eps=std::stod(argv[4]);
  auto start=std::chrono::steady_clock::now();
  try{
    M a=read(argv[1]),b=read(argv[2]);nf=a.number_of_faces();ng=b.number_of_faces();
    {CGAL::Polyhedral_envelope<K>env(a,eps);forward=env(b);}
    {CGAL::Polyhedral_envelope<K>env(b,eps);reverse=env(a);}
    if(!forward||!reverse)throw std::runtime_error("Whole-triangle envelope membership refused");
  }catch(const std::exception&e){error=e.what();}
  struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
  std::ofstream out(argv[3]);out<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"complete_symmetric_envelopes_passed":"symmetric_envelopes_refused")<<"\",\"error\":\""<<error<<"\",\"source_faces\":"<<nf<<",\"candidate_faces\":"<<ng<<",\"candidate_in_source_envelope\":"<<(forward?"true":"false")<<",\"source_in_candidate_envelope\":"<<(reverse?"true":"false")<<",\"tolerance_mm\":"<<eps<<",\"peak_resident_kib\":"<<usage.ru_maxrss<<",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"scope\":\"Complete triangle queries using CGAL5.6 EPECK polyhedral envelopes; embedding and mechanics checked separately\"}\n";
  std::cout<<(error.empty()?"PASS":"REFUSED")<<" "<<error<<std::endl;return error.empty()?0:2;
}
