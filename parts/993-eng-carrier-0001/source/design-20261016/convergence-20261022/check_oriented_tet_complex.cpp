#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Interval_nt.h>
#include <CGAL/FPU.h>
#include <array>
#include <vector>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <numeric>
#include <cstdint>
#include <stdexcept>
#include <iomanip>
#include <tuple>
using K=CGAL::Exact_predicates_inexact_constructions_kernel;
using P=std::array<double,3>;
using T=std::array<uint64_t,4>;
struct Face {uint32_t a,b,c,owner;};
static bool lesskey(const Face&x,const Face&y){return std::tie(x.a,x.b,x.c)<std::tie(y.a,y.b,y.c);}
static bool samekey(const Face&x,const Face&y){return x.a==y.a&&x.b==y.b&&x.c==y.c;}
static Face makeface(uint32_t a,uint32_t b,uint32_t c,uint32_t owner){
 unsigned parity=((a>b)+(a>c)+(b>c))&1;
 if(a>b)std::swap(a,b);if(b>c)std::swap(b,c);if(a>b)std::swap(a,b);
 if(a==b||b==c)throw std::runtime_error("Repeated face vertex");
 return {a,b,c,owner|(parity<<31)};
}
static void radix(std::vector<Face>&faces){
 std::vector<Face> tmp(faces.size());
 for(int axis=2;axis>=0;--axis)for(unsigned shift=0;shift<32;shift+=8){
  auto digit=[&](const Face&f){uint32_t key=axis==0?f.a:(axis==1?f.b:f.c);return (key>>shift)&255;};
  std::array<size_t,256> count{},pos{};
  for(const auto&f:faces)++count[digit(f)];
  if(*std::max_element(count.begin(),count.end())==faces.size())continue;
  for(int i=1;i<256;++i)pos[i]=pos[i-1]+count[i-1];
  for(const auto&f:faces)tmp[pos[digit(f)]++]=f;
  faces.swap(tmp);
 }
}
struct DSU{
 std::vector<uint32_t> p;std::vector<uint8_t> rank;uint64_t components;
 DSU(size_t n):p(n),rank(n,0),components(n){std::iota(p.begin(),p.end(),0);}
 uint32_t find(uint32_t x){while(p[x]!=x){p[x]=p[p[x]];x=p[x];}return x;}
 void join(uint32_t a,uint32_t b){a=find(a);b=find(b);if(a==b)return;if(rank[a]<rank[b])std::swap(a,b);p[b]=a;if(rank[a]==rank[b])++rank[a];--components;}
};
int main(int argc,char**argv){
 if(argc!=9){std::cerr<<"Usage: CHECK ARCHIVE V_OFFSET NV T_OFFSET NT T_FORTRAN SOURCE_MESH64 REPORT\n";return 2;}
 uint64_t checked=0,boundary=0,interior=0;double maxupper=0,minlower=1e300;std::string error;uint64_t components=0,unused=0;
 try{
  const uint64_t vo=std::stoull(argv[2]),nv=std::stoull(argv[3]),to=std::stoull(argv[4]),nt=std::stoull(argv[5]);
  if(!nv||!nt||nv>=0x80000000ull||nt>=0x80000000ull)throw std::runtime_error("Count exceeds admitted 31-bit owner/index layout");
  std::ifstream archive(argv[1],std::ios::binary);if(!archive)throw std::runtime_error("Archive unavailable");
  std::vector<P> vertices(nv);std::vector<T> tets(nt);archive.seekg(vo);archive.read(reinterpret_cast<char*>(vertices.data()),nv*sizeof(P));if(!archive)throw std::runtime_error("Incomplete vertex payload");archive.seekg(to);archive.read(reinterpret_cast<char*>(tets.data()),nt*sizeof(T));if(!archive)throw std::runtime_error("Incomplete cell payload");
  for(const auto&p:vertices)for(double x:p)if(!std::isfinite(x))throw std::runtime_error("Nonfinite coordinate");
  const bool fortran=std::string(argv[6])=="1";
  auto loadtet=[&](size_t i){if(!fortran)return tets[i];const auto*raw=reinterpret_cast<const uint64_t*>(tets.data());return T{raw[i],raw[i+nt],raw[i+2*nt],raw[i+3*nt]};};
  std::ifstream source(argv[7]);uint64_t snv,snf;source>>snv>>snf;if(!source||snv>nv)throw std::runtime_error("Invalid source boundary counts");
  for(uint64_t i=0;i<snv;++i){P p;source>>p[0]>>p[1]>>p[2];if(!source||p!=vertices[i])throw std::runtime_error("Original vertex changed");}
  std::vector<Face> expected;expected.reserve(snf);
  for(uint64_t i=0;i<snf;++i){uint64_t a,b,c;source>>a>>b>>c;if(!source||a>=snv||b>=snv||c>=snv)throw std::runtime_error("Invalid original face index");expected.push_back(makeface(a,b,c,0));}
  std::sort(expected.begin(),expected.end(),lesskey);for(size_t i=1;i<expected.size();++i)if(samekey(expected[i-1],expected[i]))throw std::runtime_error("Duplicate source boundary facet");
  std::vector<Face> faces;faces.reserve(4*nt);std::vector<uint8_t> used(nv,0);
  const unsigned patterns[4][3]={{1,2,3},{0,3,2},{0,1,3},{0,2,1}};
  for(uint64_t i=0;i<nt;++i){const T t=loadtet(i);for(auto j:t){if(j>=nv)throw std::runtime_error("Invalid cell index");used[j]=1;}auto sorted=t;std::sort(sorted.begin(),sorted.end());if(std::adjacent_find(sorted.begin(),sorted.end())!=sorted.end())throw std::runtime_error("Repeated cell vertex");
   auto point=[&](uint64_t j){const auto&p=vertices[j];return K::Point_3(p[0],p[1],p[2]);};
   if(CGAL::orientation(point(t[0]),point(t[1]),point(t[2]),point(t[3]))!=CGAL::POSITIVE)throw std::runtime_error("Cell lacks exact positive orientation");++checked;
   for(const auto&pat:patterns)faces.push_back(makeface(t[pat[0]],t[pat[1]],t[pat[2]],i));
  }
  unused=std::count(used.begin(),used.end(),0);
  {
   CGAL::Protect_FPU_rounding<true> guard(CGAL_FE_UPWARD);using I=CGAL::Interval_nt<false>;
   for(size_t i=0;i<nt;++i){const T t=loadtet(i);std::array<I,3>a,b,c;for(int j=0;j<3;++j){a[j]=I(vertices[t[1]][j])-I(vertices[t[0]][j]);b[j]=I(vertices[t[2]][j])-I(vertices[t[0]][j]);c[j]=I(vertices[t[3]][j])-I(vertices[t[0]][j]);}I volume=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/I(6);maxupper=std::max(maxupper,volume.sup());minlower=std::min(minlower,volume.inf());}
  }
  if(maxupper>.5)throw std::runtime_error("Certified maximum volume exceeds fixed 0.5 mm3 limit");
  radix(faces);DSU dsu(nt);size_t reference=0;
  for(size_t begin=0;begin<faces.size();){size_t end=begin+1;while(end<faces.size()&&samekey(faces[begin],faces[end]))++end;
   if(end-begin==2){const auto&a=faces[begin];const auto&b=faces[begin+1];if((a.owner>>31)==(b.owner>>31))throw std::runtime_error("Interior face orientations do not cancel");dsu.join(a.owner&0x7fffffff,b.owner&0x7fffffff);++interior;}
   else if(end-begin==1){const auto&f=faces[begin];if(reference>=expected.size()||!samekey(f,expected[reference])||(f.owner>>31)!=(expected[reference].owner>>31))throw std::runtime_error("Indexed oriented boundary differs from frozen source");++reference;++boundary;}
   else throw std::runtime_error("Nonmanifold facet incidence");begin=end;
  }
  if(reference!=expected.size())throw std::runtime_error("Original boundary facet missing");components=dsu.components;if(components!=1)throw std::runtime_error("Cell adjacency is disconnected");
 }catch(const std::exception&e){error=e.what();}
 std::ofstream out(argv[8]);out<<std::setprecision(17)<<"{\n  \"status\": \""<<(error.empty()?"exact_orientations_and_indexed_boundary_passed":"volume_refused")<<"\",\n  \"error\": \""<<error<<"\",\n  \"exact_positive_cells\": "<<checked<<",\n  \"oriented_boundary_faces\": "<<boundary<<",\n  \"oppositely_oriented_interior_faces\": "<<interior<<",\n  \"cell_components\": "<<components<<",\n  \"unused_vertices\": "<<unused<<",\n  \"maximum_interval_volume_upper_mm3\": "<<maxupper<<",\n  \"minimum_interval_volume_lower_mm3\": "<<minlower<<",\n  \"mechanical_mesh_admitted\": false,\n  \"manufacturing_authorized\": false\n}\n";std::cout<<(error.empty()?"PASS":"REFUSED")<<" "<<error<<std::endl;return error.empty()?0:2;
}
