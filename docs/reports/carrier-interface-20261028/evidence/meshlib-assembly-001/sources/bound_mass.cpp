#include <algorithm>
#include <array>
#include <cfenv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
struct I {double lo,hi;};
double down(double x){return std::nextafter(x,-INFINITY);}
double up(double x){return std::nextafter(x,INFINITY);}
I add(I a,I b){return {down(a.lo+b.lo),up(a.hi+b.hi)};}
I sub(I a,I b){return {down(a.lo-b.hi),up(a.hi-b.lo)};}
I mul(I a,I b){double x[]={a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};return {down(*std::min_element(x,x+4)),up(*std::max_element(x,x+4))};}
I divi(I a,I b){if(b.lo<=0&&b.hi>=0)throw std::runtime_error("Interval denominator contains zero");double x[]={a.lo/b.lo,a.lo/b.hi,a.hi/b.lo,a.hi/b.hi};return {down(*std::min_element(x,x+4)),up(*std::max_element(x,x+4))};}
using P=std::array<double,3>;
I point(double x){return {x,x};}
I volume(P a,P b,P c){
 I x=sub(mul(point(b[1]),point(c[2])),mul(point(b[2]),point(c[1])));
 I y=sub(mul(point(b[2]),point(c[0])),mul(point(b[0]),point(c[2])));
 I z=sub(mul(point(b[0]),point(c[1])),mul(point(b[1]),point(c[0])));
 return divi(add(add(mul(point(a[0]),x),mul(point(a[1]),y)),mul(point(a[2]),z)),{6,6});
}
int main(int argc,char**argv){
 static_assert(std::numeric_limits<double>::is_iec559&&sizeof(double)==8);
 if(argc!=3)return 2;
 auto start=std::chrono::steady_clock::now();I total{0,0},mass{0,0};uint64_t nv=0,nf=0,checked=0;std::string error;
 try{
 if(std::fegetround()!=FE_TONEAREST)throw std::runtime_error("Round-to-nearest required");
 volatile double tiny=std::numeric_limits<double>::denorm_min();
 if(tiny*1.0==0||std::nextafter(0.0,1.0)!=tiny)throw std::runtime_error("Subnormal preservation required");
 std::ifstream in(argv[1],std::ios::binary);in.read((char*)&nv,8);in.read((char*)&nf,8);
 if(!in||!nv||!nf||nv>100000000||nf>200000000)throw std::runtime_error("Invalid counts");
 std::vector<P>v(nv);in.read((char*)v.data(),nv*24);for(auto p:v)for(auto x:p)if(!std::isfinite(x)||std::abs(x)>1e6)throw std::runtime_error("Invalid coordinate");
 I block{0,0};
 for(uint64_t i=0;i<nf;++i){
 uint64_t f[3];in.read((char*)f,24);if(!in||f[0]>=nv||f[1]>=nv||f[2]>=nv)throw std::runtime_error("Invalid face");
 block=add(block,volume(v[f[0]],v[f[1]],v[f[2]]));++checked;
 if((i+1)%1000==0){total=add(total,block);block={0,0};}
 }
 if(in.peek()!=EOF)throw std::runtime_error("Trailing bytes");
 total=add(total,block);mass=mul(total,divi({442,442},{100000000,100000000}));
 if(!std::isfinite(total.lo)||!std::isfinite(total.hi)||total.lo>total.hi)throw std::runtime_error("Nonfinite or reversed interval");
 }catch(const std::exception&e){error=e.what();}
 bool under=error.empty()&&mass.lo>0&&mass.hi<down(1.3);
 std::ofstream out(argv[2]);out<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"signed_volume_interval_computed":"interval_refused")<<"\",\"error\":\""<<error<<"\",\"vertices\":"<<nv<<",\"faces\":"<<nf<<",\"faces_checked\":"<<checked<<",\"volume_lower_mm3\":"<<total.lo<<",\"volume_upper_mm3\":"<<total.hi<<",\"mass_lower_kg\":"<<mass.lo<<",\"mass_upper_kg\":"<<mass.hi<<",\"below_1_30_kg\":"<<(under?"true":"false")<<",\"density_exact_numerator\":442,\"density_exact_denominator\":100000000,\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"scope\":\"Outward-rounded arithmetic on the exact represented vertex coordinates. Topology and embedding are separate prerequisites. Density is a declared nominal model input.\"}\n";
 return error.empty()?0:2;
}
