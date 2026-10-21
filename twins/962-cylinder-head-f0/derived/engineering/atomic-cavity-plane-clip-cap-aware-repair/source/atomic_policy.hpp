// Separate simultaneous quotient candidate. No SMS queue/intermediate collapses.
#define main preserved_quality_patch_entrypoint
#include "quality_patch.cpp"
#undef main
#include <CGAL/Polyhedral_envelope.h>
#include <CGAL/number_utils.h>
#include <algorithm>
#include <limits>
#include <map>
#include <numeric>
#include <set>

using Row=std::array<std::size_t,3>;
using Edge=std::pair<std::size_t,std::size_t>;
struct Rejected:std::runtime_error { using std::runtime_error::runtime_error; };
struct UF {
  std::vector<std::size_t> p;
  explicit UF(std::size_t n):p(n) { std::iota(p.begin(),p.end(),0); }
  std::size_t find(std::size_t v) { while(v!=p[v]) {p[v]=p[p[v]];v=p[v];}return v; }
  void join(std::size_t a,std::size_t b) {a=find(a);b=find(b);if(a!=b)p[std::max(a,b)]=std::min(a,b);}
};
bool same_point_bits(const Point& a,const Point& b) {
  std::array<double,3> x{a.x(),a.y(),a.z()},y{b.x(),b.y(),b.z()};return std::memcmp(x.data(),y.data(),sizeof(x))==0;
}
Row oriented(Row a) { return std::min({a,Row{a[1],a[2],a[0]},Row{a[2],a[0],a[1]}}); }
std::vector<Edge> pairs(const fs::path& path) {
  auto bytes=fs::file_size(path);if(!bytes||bytes%16||bytes>135*16)throw std::runtime_error("Invalid fixed pair file");
  std::ifstream in(path,std::ios::binary);std::vector<Edge> out;
  while(out.size()<bytes/16) {auto a=read_value<std::uint64_t>(in),b=read_value<std::uint64_t>(in);out.emplace_back(a,b);}
  if(!std::is_sorted(out.begin(),out.end())||std::adjacent_find(out.begin(),out.end())!=out.end())throw std::runtime_error("Sorted unique pair rows required");
  return out;
}
using Chain=std::map<Edge,long>;
void chain_add(Chain& c,Row t) {
  for(int i=0;i<3;++i) {auto a=t[i],b=t[(i+1)%3];Edge e{std::min(a,b),std::max(a,b)};c[e]+=a<b?1:-1;if(!c[e])c.erase(e);}
}
struct Topology {bool valid=false;std::size_t components=0;long long euler=0;};
Topology topology(const Mesh& m) {
  Topology s;if(!CGAL::is_closed(m)||!CGAL::is_triangle_mesh(m)||!CGAL::is_valid_polygon_mesh(m))return s;
  std::vector<std::size_t> incidence(m.num_vertices(),0);UF uf(m.num_vertices());
  for(auto f:m.faces())for(auto v:vertices(m,f))++incidence[v.idx()];
  for(auto e:m.edges()) {auto h=m.halfedge(e);uf.join(m.source(h).idx(),m.target(h).idx());}
  for(auto v:m.vertices()) {
    if(!incidence[v.idx()])return s;std::size_t count=0;
    for(auto h:CGAL::halfedges_around_target(m.halfedge(v),m)) {
      if(m.target(h)!=v||++count>incidence[v.idx()])return s;
    }
    if(count!=incidence[v.idx()])return s;if(uf.find(v.idx())==v.idx())++s.components;
  }
  s.euler=static_cast<long long>(m.number_of_vertices())-static_cast<long long>(m.number_of_edges())+static_cast<long long>(m.number_of_faces());s.valid=true;return s;
}
// Same scalar policy/operation order as CGAL5.6 Edge_collapse.h shared-triangle
// predicate and constructor: strict squared-area ratio1e8, then cos(1degree)^2.
int ordinary(const Point& p0,const Point& p1,const Point& p2,const Point& p3) {
  Kernel traits;auto e01=traits.construct_vector_3_object()(p0,p1),e02=traits.construct_vector_3_object()(p0,p2),e03=traits.construct_vector_3_object()(p0,p3);
  auto n012=traits.construct_cross_product_vector_3_object()(e01,e02),n023=traits.construct_cross_product_vector_3_object()(e02,e03);
  auto l012=traits.compute_scalar_product_3_object()(n012,n012),l023=traits.compute_scalar_product_3_object()(n023,n023);
  auto larger=(std::max)(l012,l023),smaller=(std::min)(l012,l023);
  if(!(larger<1e8*smaller))return 1;
  auto dot=traits.compute_scalar_product_3_object()(n012,n023);if(CGAL_NTS is_positive(dot))return 0;
  const double max_cos_squared=CGAL::square(std::cos(1.0*CGAL_PI/180.0));
  return dot*dot<=max_cos_squared*(l012*l023)?0:2;
}
