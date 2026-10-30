#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <vector>
#include <chrono>
struct P {double x,y,z;};
P operator-(P a,P b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
P cross(P a,P b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
double dot(P a,P b){return a.x*b.x+a.y*b.y+a.z*b.z;}
double norm(P a){return std::hypot(a.x,a.y,a.z);}
struct UF {
 std::vector<uint32_t> p;std::vector<uint8_t> rank;
 UF(size_t n):p(n),rank(n,0){std::iota(p.begin(),p.end(),0);}
 uint32_t find(uint32_t a){while(p[a]!=a){p[a]=p[p[a]];a=p[a];}return a;}
 void join(uint32_t a,uint32_t b){a=find(a);b=find(b);if(a==b)return;if(rank[a]<rank[b])std::swap(a,b);p[b]=a;if(rank[a]==rank[b])++rank[a];}
};
struct E {uint64_t key;uint32_t c;};
struct W {double angle,length;uint32_t u,v;};
uint32_t next(uint32_t c){return c-c%3+(c+1)%3;}
int main(int argc,char**argv){
 if(argc!=4)return 2;
 std::ofstream features(argv[3]);features<<std::setprecision(17)<<"u,v,face_a,face_b,angle_degrees,length_mm,ax,ay,az,bx,by,bz\n";
 auto start=std::chrono::steady_clock::now();
 uint64_t nv=0,nf=0,ne=0,unused=0,nonmanifold=0;std::string error;
 std::array<uint64_t,7> counts{};std::array<double,7> thresholds{1,5,15,30,45,60,90};
 uint64_t severe_protected=0;std::vector<W>worst;std::vector<P>v;std::vector<double>component_volumes;
 try{
 std::ifstream in(argv[1],std::ios::binary);in.read((char*)&nv,8);in.read((char*)&nf,8);
 if(!in||nv==0||nf==0||nv>=UINT32_MAX||nf>=UINT32_MAX/3)throw std::runtime_error("Unsupported counts");
 v.resize(nv);in.read((char*)v.data(),24*nv);for(auto a:v)if(!std::isfinite(a.x)||!std::isfinite(a.y)||!std::isfinite(a.z))throw std::runtime_error("Nonfinite vertex");
 std::vector<uint32_t>f(nf*3);std::vector<P>normals(nf);std::vector<E>edges;edges.reserve(nf*3);
 for(uint32_t i=0;i<nf;++i){
  uint64_t ids[3];in.read((char*)ids,24);
  if(!in||ids[0]>=nv||ids[1]>=nv||ids[2]>=nv)throw std::runtime_error("Invalid index");
  P n=cross(v[ids[1]]-v[ids[0]],v[ids[2]]-v[ids[0]]);double len=norm(n);
  if(!(len>0)||!std::isfinite(len))throw std::runtime_error("Degenerate face");
  normals[i]={n.x/len,n.y/len,n.z/len};
  for(uint32_t k=0;k<3;++k){uint32_t a=ids[k],b=ids[(k+1)%3];f[3*i+k]=a;edges.push_back({(uint64_t(std::min(a,b))<<32)|std::max(a,b),3*i+k});}
 }
 if(in.peek()!=EOF)throw std::runtime_error("Trailing bytes");
 std::cout<<"INPUT_LOADED "<<nv<<" "<<nf<<std::endl;
 std::sort(edges.begin(),edges.end(),[](E a,E b){return a.key<b.key;});
 UF corners(nf*3),faces(nf);ne=0;
 for(size_t i=0;i<edges.size();){
  size_t j=i+1;while(j<edges.size()&&edges[j].key==edges[i].key)++j;
  if(j-i!=2)throw std::runtime_error("Edge incidence is not two");
  uint32_t c=edges[i].c,d=edges[i+1].c,u=f[c],w=f[next(c)];
  if(u!=f[next(d)]||w!=f[d])throw std::runtime_error("Inconsistent edge orientation");
  corners.join(c,next(d));corners.join(next(c),d);faces.join(c/3,d/3);
  P delta=v[w]-v[u];double length=norm(delta);if(!(length>0))throw std::runtime_error("Zero edge");
  double angle=std::atan2(dot(delta,cross(normals[c/3],normals[d/3]))/length,dot(normals[c/3],normals[d/3]))*180/std::acos(-1.0);
  for(size_t k=0;k<7;++k)counts[k]+=angle < -thresholds[k];
  if(angle < -45)features<<u<<","<<w<<","<<c/3<<","<<d/3<<","<<angle<<","<<length<<","<<v[u].x<<","<<v[u].y<<","<<v[u].z<<","<<v[w].x<<","<<v[w].y<<","<<v[w].z<<"\n";
  if(angle < -45){double x=(v[u].x+v[w].x)/2;severe_protected+=std::abs(x)<=65||std::abs(x)>=260;}
  if(worst.size()<20||angle<worst.back().angle){worst.push_back({angle,length,u,w});std::sort(worst.begin(),worst.end(),[](W a,W b){return a.angle<b.angle;});if(worst.size()>20)worst.pop_back();}
  ++ne;i=j;
 }
 std::vector<uint32_t>first(nv,UINT32_MAX);std::vector<uint8_t>bad(nv,0);
 for(uint32_t c=0;c<f.size();++c){uint32_t root=corners.find(c),vertex=f[c];if(first[vertex]==UINT32_MAX)first[vertex]=root;else if(first[vertex]!=root)bad[vertex]=1;}
 for(size_t i=0;i<nv;++i){unused+=first[i]==UINT32_MAX;nonmanifold+=bad[i];}
 if(nonmanifold)throw std::runtime_error("Disconnected face fans at used vertices");
 std::vector<uint32_t>component(nf,UINT32_MAX);std::vector<long double>sums,corrections;
 for(uint32_t i=0;i<nf;++i){
  uint32_t root=faces.find(i);if(component[root]==UINT32_MAX){component[root]=sums.size();sums.push_back(0);corrections.push_back(0);}
  uint32_t k=component[root];long double value=dot(v[f[3*i]],cross(v[f[3*i+1]],v[f[3*i+2]]))/6.0L;
  long double y=value-corrections[k],t=sums[k]+y;corrections[k]=(t-sums[k])-y;sums[k]=t;
 }
 for(auto value:sums)component_volumes.push_back(double(value));
 }catch(const std::exception&e){error=e.what();}
 std::ofstream out(argv[2]);out<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"closed_oriented_vertex_manifold":"topology_refused")<<"\",\"error\":\""<<error<<"\",\"vertices\":"<<nv<<",\"faces\":"<<nf<<",\"edges\":"<<ne<<",\"unused_vertices\":"<<unused<<",\"nonmanifold_used_vertices\":"<<nonmanifold<<",\"boundary_components\":"<<component_volumes.size()<<",\"component_signed_volumes_mm3\":[";
 for(size_t i=0;i<component_volumes.size();++i){if(i)out<<",";out<<component_volumes[i];}
 out<<"],\"reentrant_edges_above_degrees\":{";
 for(size_t k=0;k<7;++k){if(k)out<<",";out<<"\""<<thresholds[k]<<"\":"<<counts[k];}
 out<<"},\"severe_edges_in_protected_x_regions\":"<<severe_protected<<",\"worst_edges\":[";
 for(size_t i=0;i<worst.size();++i){if(i)out<<",";auto a=worst[i];out<<"{\"angle_degrees\":"<<a.angle<<",\"length_mm\":"<<a.length<<",\"vertices\":["<<a.u<<","<<a.v<<"],\"midpoint_mm\":["<<(v[a.u].x+v[a.v].x)/2<<","<<(v[a.u].y+v[a.v].y)/2<<","<<(v[a.u].z+v[a.v].z)/2<<"]}";}
 out<<"],\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"exact_volume_certified\":false,\"mechanical_admissibility_established\":false}\n";
 return error.empty()?0:2;
}
