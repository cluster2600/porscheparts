#include <fastenvelope/FastEnvelope.h>
#include <Predicates_psm.h>
#include <array>
#include <chrono>
#include <cmath>
#include <cfenv>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
using fastEnvelope::Vector3;using fastEnvelope::Vector3i;using fastEnvelope::FastEnvelope;
static_assert(sizeof(fastEnvelope::Scalar)==8,"Binary64 geometry required");
struct Mesh {std::vector<Vector3> v;std::vector<Vector3i> f;};
void require(bool b,const char*s){if(!b)throw std::runtime_error(s);}
Mesh read(const char*path){std::ifstream in(path);std::size_t nv,nf;in>>nv>>nf;require(bool(in)&&nv>0&&nf>0&&nv<std::size_t(std::numeric_limits<int>::max()),"Bounded nonempty mesh required");Mesh m;std::vector<bool>used(nv,false);for(std::size_t i=0;i<nv;++i){double x,y,z;in>>x>>y>>z;require(bool(in)&&std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z),"Finite coordinates required");m.v.emplace_back(x,y,z);}for(std::size_t i=0;i<nf;++i){std::size_t a,b,c;in>>a>>b>>c;require(bool(in)&&a<nv&&b<nv&&c<nv&&a!=b&&a!=c&&b!=c,"Triangle indices invalid");require((m.v[b]-m.v[a]).cross(m.v[c]-m.v[a]).squaredNorm()>0,"Degenerate triangle forbidden");m.f.emplace_back(int(a),int(b),int(c));used[a]=used[b]=used[c]=true;}std::string extra;require(!(in>>extra)&&in.eof(),"Trailing mesh data");for(bool b:used)require(b,"Unused vertex");return m;}
std::array<Vector3,3> tri(const Mesh&m,const Vector3i&f){return {m.v[f[0]],m.v[f[1]],m.v[f[2]]};}
void controls(){
 require(std::fesetround(FE_UPWARD)==0,"Upward rounding unavailable");volatile double a=1.,b=std::ldexp(1.,-53);volatile double c=a+b;require(c>1.,"GCC directed rounding control failed");require(std::fesetround(FE_TONEAREST)==0,"Nearest rounding unavailable");
 Mesh plane{{Vector3(0,0,0),Vector3(1,0,0),Vector3(0,1,0)},{Vector3i(0,1,2)}};FastEnvelope e(plane.v,plane.f,.003);std::array<Vector3,3>q={Vector3(.1,.1,0),Vector3(.2,.1,0),Vector3(.1,.2,0)};require(!e.is_outside(q),"Coplanar triangle control failed");for(auto&p:q)p[2]=.0002;require(!e.is_outside(q),"Inside-envelope control failed");for(auto&p:q)p[2]=.02;require(e.is_outside(q),"Outside-envelope control failed");
 Mesh saddle{{Vector3(0,0,0),Vector3(1,0,0),Vector3(1,1,.2),Vector3(0,1,0)},{Vector3i(0,1,2),Vector3i(0,2,3)}};FastEnvelope folded(saddle.v,saddle.f,.003);for(const auto&p:saddle.v)require(!folded.is_outside(p),"Shared-vertex control failed");require(folded.is_outside(std::array<Vector3,3>{saddle.v[0],saddle.v[1],saddle.v[3]})||folded.is_outside(std::array<Vector3,3>{saddle.v[1],saddle.v[2],saddle.v[3]}),"Triangle-interior counterexample was missed");
}
int main(int argc,char**argv){try{require(argc==4,"REFERENCE CANDIDATE OUTPUT.json");GEO::PCK::initialize();controls();std::cout<<"GCC rounding and envelope controls passed"<<std::endl;auto reference=read(argv[1]),candidate=read(argv[2]);auto start=std::chrono::steady_clock::now();std::size_t rejected_forward=0,rejected_reverse=0;{FastEnvelope e(reference.v,reference.f,.003);for(const auto&f:candidate.f)if(e.is_outside(tri(candidate,f)))++rejected_forward;}std::cout<<"candidate-to-reference checked"<<std::endl;{FastEnvelope e(candidate.v,candidate.f,.003);for(const auto&f:reference.f)if(e.is_outside(tri(reference,f)))++rejected_reverse;}bool pass=!rejected_forward&&!rejected_reverse;std::ofstream out(argv[3]);out<<std::boolalpha<<"{\"status\":\""<<(pass?"symmetric_complete_triangle_envelope_containment_passed":"conservative_envelope_containment_not_established")<<"\",\"epsilon_mm\":0.003,\"controls_passed\":true,\"scalar_bytes\":8,\"reference_faces\":"<<reference.f.size()<<",\"candidate_faces\":"<<candidate.f.size()<<",\"candidate_triangles_not_certified\":"<<rejected_forward<<",\"reference_triangles_not_certified\":"<<rejected_reverse<<",\"complete_faces_checked\":true,\"exact_envelope_predicates_requested\":true,\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"manufacturing_authorized\":false}\n";require(bool(out),"Output write failed");return pass?0:3;}catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 70;}}
