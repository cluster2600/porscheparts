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
Q compact(Q x){return Q(CGAL::exact(x));}
void event(std::map<Key,int64_t>&events,Key key,int delta){
 for(auto&x:key)x=compact(x);
 auto result=events.emplace(key,delta);
 if(!result.second){result.first->second+=delta;if(result.first->second==0)events.erase(result.first);}
}
void boundary(const Mesh&m,const Edge&e,int weight,std::map<Key,int64_t>&events){
 const auto&f=m.f[e.face];auto normal=CGAL::cross_product(m.v[f[1]]-m.v[f[0]],m.v[f[2]]-m.v[f[0]]);
 std::array<Q,3>n={normal.x(),normal.y(),normal.z()};int ni=0;while(n[ni]==0)++ni;
 Q scale=n[ni];Key key;
 for(int k=0;k<3;++k)key[k]=n[k]/scale;
 const auto&p=m.v[f[0]];key[3]=-(n[0]*p.x()+n[1]*p.y()+n[2]*p.z())/scale;
 const auto&a=m.v[e.increasing?e.low:e.high];const auto&b=m.v[e.increasing?e.high:e.low];
 std::array<Q,3>av={a.x(),a.y(),a.z()},bv={b.x(),b.y(),b.z()},d;
 for(int k=0;k<3;++k)d[k]=bv[k]-av[k];int axis=0;while(d[axis]==0)++axis;
 Q ds=d[axis];for(int k=0;k<3;++k)d[k]/=ds;
 for(int k=0;k<3;++k){key[4+k]=d[k];key[7+k]=av[k]-d[k]*av[axis];}
 key[10]=av[axis];event(events,key,weight);
 key[10]=bv[axis];event(events,key,-weight);
}
uint64_t accumulate(const Mesh&m,int weight,std::map<Key,int64_t>&events){
 std::vector<Edge>edges;edges.reserve(m.f.size()*3);
 for(uint64_t i=0;i<m.f.size();++i)for(int j=0;j<3;++j){uint64_t a=m.f[i][j],b=m.f[i][(j+1)%3];edges.push_back({std::min(a,b),std::max(a,b),i,a<b});}
 std::sort(edges.begin(),edges.end(),[](const Edge&a,const Edge&b){return a.low<b.low||(a.low==b.low&&a.high<b.high);});
 uint64_t count=0;
 for(size_t i=0;i<edges.size();){
  size_t end=i+1;while(end<edges.size()&&edges[end].low==edges[i].low&&edges[end].high==edges[i].high)++end;
  if(end-i==1){boundary(m,edges[i],weight,events);++count;i=end;continue;}
  if(end-i!=2||edges[i].increasing==edges[i+1].increasing)throw std::runtime_error("Residual oriented edge incidence invalid");
  const auto&a=m.f[edges[i].face];const auto&b=m.f[edges[i+1].face];uint64_t fourth=b[0];for(auto id:b)if(id!=edges[i].low&&id!=edges[i].high)fourth=id;
  bool same=CGAL::coplanar(m.v[a[0]],m.v[a[1]],m.v[a[2]],m.v[fourth]);
  if(same){
   auto na=CGAL::cross_product(m.v[a[1]]-m.v[a[0]],m.v[a[2]]-m.v[a[0]]);
   auto nb=CGAL::cross_product(m.v[b[1]]-m.v[b[0]],m.v[b[2]]-m.v[b[0]]);
   if(na*nb<=0)throw std::runtime_error("Overlapping oppositely oriented coplanar neighbors");
  }else{boundary(m,edges[i],weight,events);boundary(m,edges[i+1],weight,events);count+=2;}
  i=end;
 }
 return count;
}
int main(int argc,char**argv){
 if(argc!=4||std::filesystem::exists(argv[3]))return 2;
 auto start=std::chrono::steady_clock::now();std::string error;uint64_t nf=0,ng=0,ba=0,bb=0,unmatched=0;bool equal=false;
 try{
  Mesh a=read(argv[1]),b=read(argv[2]);nf=a.f.size();ng=b.f.size();cancel_identical(a,b);std::map<Key,int64_t>events;
  ba=accumulate(a,1,events);std::cout<<"SOURCE_BOUNDARY "<<ba<<" "<<events.size()<<std::endl;
  bb=accumulate(b,-1,events);unmatched=events.size();equal=events.empty();
  if(!equal)throw std::runtime_error("Exact oriented planar boundaries differ");
 }catch(const std::exception&e){error=e.what();}
 struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::ofstream o(argv[3]);o<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"exact_oriented_planar_boundaries_equal":"exact_planar_equality_refused")<<"\",\"error\":\""<<error<<"\",\"source_faces\":"<<nf<<",\"candidate_faces\":"<<ng<<",\"source_patch_boundary_edges\":"<<ba<<",\"candidate_patch_boundary_edges\":"<<bb<<",\"unmatched_line_events\":"<<unmatched<<",\"exact_oriented_boundaries_equal\":"<<(equal?"true":"false")<<",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peak_resident_kib\":"<<usage.ru_maxrss<<",\"scope\":\"All triangles covered by exact oriented coordinate cancellation or rational planar boundary equality; separately established complete embedded oriented inputs required\"}\n";
 std::cout<<(error.empty()?"PASS":"REFUSED")<<" "<<error<<std::endl;return error.empty()?0:2;
}
