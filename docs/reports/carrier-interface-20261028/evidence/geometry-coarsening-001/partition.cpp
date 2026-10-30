#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/number_utils.h>
#include <array>
#include <vector>
#include <map>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <sys/resource.h>
using K=CGAL::Exact_predicates_exact_constructions_kernel;using Q=K::FT;
using Face=std::array<uint64_t,3>;using Key=std::array<Q,11>;
struct Mesh{std::vector<K::Point_3>v;std::vector<Face>f;std::vector<std::array<double,3>> raw;};
struct Edge{uint64_t low,high,face;bool increasing;};
Mesh read(const char*path){
 std::ifstream in(path,std::ios::binary);uint64_t nv=0,nf=0;in.read((char*)&nv,8);in.read((char*)&nf,8);
 if(!in||!nv||!nf||nv>20000000||nf>40000000)throw std::runtime_error("Invalid header");
 Mesh m;m.v.reserve(nv);m.f.reserve(nf);
 for(uint64_t i=0;i<nv;++i){double p[3];in.read((char*)p,24);if(!in||!std::isfinite(p[0])||!std::isfinite(p[1])||!std::isfinite(p[2]))throw std::runtime_error("Invalid point");m.v.emplace_back(p[0],p[1],p[2]);m.raw.push_back({p[0],p[1],p[2]});}
 for(uint64_t i=0;i<nf;++i){Face f;in.read((char*)f.data(),24);if(!in||f[0]>=nv||f[1]>=nv||f[2]>=nv||CGAL::collinear(m.v[f[0]],m.v[f[1]],m.v[f[2]]))throw std::runtime_error("Invalid or degenerate triangle");m.f.push_back(f);}
 char extra;if(in.read(&extra,1))throw std::runtime_error("Unexpected trailing bytes");return m;
}
uint64_t common_triangles=0;
void cancel_identical(Mesh&a,Mesh&b){
 std::map<std::array<double,3>,uint64_t> ids;
 struct Record{Face key;uint64_t index;};
 auto records=[&](const Mesh&m){
  std::vector<uint64_t> vertices;vertices.reserve(m.raw.size());
  for(const auto&p:m.raw){auto it=ids.emplace(p,ids.size());vertices.push_back(it.first->second);}
  std::vector<Record> rows;rows.reserve(m.f.size());
  for(uint64_t i=0;i<m.f.size();++i){Face key;for(int k=0;k<3;++k)key[k]=vertices[m.f[i][k]];int first=std::min_element(key.begin(),key.end())-key.begin();rows.push_back({{key[first],key[(first+1)%3],key[(first+2)%3]},i});}
  std::sort(rows.begin(),rows.end(),[](const Record&x,const Record&y){return x.key<y.key;});return rows;
 };
 auto aa=records(a),bb=records(b);std::vector<Face>left,right;size_t i=0,j=0;
 while(i<aa.size()&&j<bb.size()){
  if(aa[i].key==bb[j].key){++common_triangles;++i;++j;}
  else if(aa[i].key<bb[j].key)left.push_back(a.f[aa[i++].index]);
  else right.push_back(b.f[bb[j++].index]);
 }
 while(i<aa.size())left.push_back(a.f[aa[i++].index]);
 while(j<bb.size())right.push_back(b.f[bb[j++].index]);
 if(left.size()+common_triangles!=a.f.size()||right.size()+common_triangles!=b.f.size())throw std::runtime_error("Triangle cancellation coverage mismatch");
 a.f=std::move(left);b.f=std::move(right);
 std::cout<<"IDENTICAL_ORIENTED_TRIANGLES "<<common_triangles<<" REMAINING "<<a.f.size()<<" "<<b.f.size()<<std::endl;
}

void write(const Mesh&m,const char*path){
 std::vector<uint64_t>map(m.v.size(),UINT64_MAX);uint64_t n=0;
 for(const auto&f:m.f)for(auto i:f)if(map[i]==UINT64_MAX)map[i]=n++;
 std::vector<std::array<double,3>>v(n);for(size_t i=0;i<map.size();++i)if(map[i]!=UINT64_MAX)v[map[i]]=m.raw[i];
 std::ofstream o(path,std::ios::binary);uint64_t nf=m.f.size();o.write((char*)&n,8);o.write((char*)&nf,8);for(const auto&p:v)o.write((char*)p.data(),24);
 for(const auto&f:m.f){Face q={map[f[0]],map[f[1]],map[f[2]]};o.write((char*)q.data(),24);}if(!o)throw std::runtime_error("Residual write failed");
}
int main(int argc,char**argv){
 if(argc!=6)return 2;for(int i=3;i<6;++i)if(std::filesystem::exists(argv[i]))return 2;
 auto start=std::chrono::steady_clock::now();std::string error;uint64_t nf=0,ng=0,rf=0,rg=0;
 try{Mesh a=read(argv[1]),b=read(argv[2]);nf=a.f.size();ng=b.f.size();cancel_identical(a,b);rf=a.f.size();rg=b.f.size();write(a,argv[3]);write(b,argv[4]);}catch(const std::exception&e){error=e.what();}
 struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::ofstream o(argv[5]);o<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"exact_oriented_triangle_partition_completed":"partition_refused")<<"\",\"error\":\""<<error<<"\",\"source_faces\":"<<nf<<",\"candidate_faces\":"<<ng<<",\"common_faces\":"<<common_triangles<<",\"source_residual_faces\":"<<rf<<",\"candidate_residual_faces\":"<<rg<<",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peak_resident_kib\":"<<usage.ru_maxrss<<",\"remaining_obligation\":\"Both complete residual soups require independent symmetric distance checks; complete input embedding remains required\"}\n";return error.empty()?0:2;
}
