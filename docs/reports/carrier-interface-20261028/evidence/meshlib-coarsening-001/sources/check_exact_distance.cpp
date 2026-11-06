#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polyhedral_envelope.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/squared_distance_3.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_triangle_primitive.h>
#include <fstream>
#include <vector>
#include <array>
#include <algorithm>
#include <unordered_map>
#include <cmath>
#include <chrono>
#include <iomanip>
#include <sys/resource.h>
using P=CGAL::Exact_predicates_inexact_constructions_kernel;
using K=CGAL::Exact_predicates_exact_constructions_kernel;
struct Mesh {std::vector<std::array<double,3>> v;std::vector<std::array<uint64_t,3>> f;};
Mesh read(const char* file){std::ifstream in(file,std::ios::binary);uint64_t nv=0,nf=0;in.read((char*)&nv,8);in.read((char*)&nf,8);if(!in||!nv||!nf||nv>20000000||nf>40000000)throw std::runtime_error("Invalid header");Mesh m;m.v.resize(nv);m.f.resize(nf);in.read((char*)m.v.data(),nv*24);in.read((char*)m.f.data(),nf*24);if(!in||in.peek()!=EOF)throw std::runtime_error("Invalid byte count");for(auto p:m.v)for(auto x:p)if(!std::isfinite(x)||std::abs(x)>1e6)throw std::runtime_error("Invalid coordinate");for(auto f:m.f)for(auto i:f)if(i>=nv)throw std::runtime_error("Invalid index");return m;}
struct Result {bool passed=false;size_t checked=0,groups=0,max_targets=0,fallback_queries=0,fallback_nodes=0,fallback_leaves=0;};
template<class Tree>
bool exact_cover(const std::array<K::Point_3,3>& triangle, Tree& tree, const K::FT& eps2,
                 size_t& total_nodes, size_t& total_leaves) {
 struct Cell {std::array<K::Point_3,3> p;unsigned depth;};
 std::vector<Cell> stack{{triangle,0}};size_t visited=0;
 while(!stack.empty()) {
  Cell cell=stack.back();stack.pop_back();++visited;++total_nodes;
  if(visited>16384)return false;
  const auto& a=cell.p[0];const auto& b=cell.p[1];const auto& c=cell.p[2];
  K::Point_3 center((a.x()+b.x()+c.x())/3,(a.y()+b.y()+c.y())/3,(a.z()+b.z()+c.z())/3);
  // Floating nearest-triangle selection is only a proposal. All three
  // distances to that SAME actual target triangle are then checked exactly.
  auto hit=tree.closest_point_and_primitive(P::Point_3(CGAL::to_double(center.x()),CGAL::to_double(center.y()),CGAL::to_double(center.z())));
  auto tri=*hit.second;
  K::Triangle_3 target(K::Point_3(tri[0].x(),tri[0].y(),tri[0].z()),
                      K::Point_3(tri[1].x(),tri[1].y(),tri[1].z()),
                      K::Point_3(tri[2].x(),tri[2].y(),tri[2].z()));
  bool covered=true;
  for(const auto& point:cell.p)if(CGAL::squared_distance(point,target)>eps2){covered=false;break;}
  if(covered){++total_leaves;continue;}
  if(cell.depth==18)return false;
  const auto ab=CGAL::midpoint(a,b),bc=CGAL::midpoint(b,c),ac=CGAL::midpoint(a,c);
  const unsigned depth=cell.depth+1;
  stack.push_back({{a,ab,ac},depth});stack.push_back({{ab,b,bc},depth});
  stack.push_back({{ac,bc,c},depth});stack.push_back({{ab,bc,ac},depth});
 }
 return true;
}

Result direction(const Mesh& query,const Mesh& target,double eps,double tile,size_t batch){
 using Iterator=std::vector<P::Triangle_3>::const_iterator;using Primitive=CGAL::AABB_triangle_primitive<P,Iterator>;using Traits=CGAL::AABB_traits<P,Primitive>;
 std::vector<P::Triangle_3> tris;tris.reserve(target.f.size());for(auto f:target.f){auto a=target.v[f[0]],b=target.v[f[1]],c=target.v[f[2]];tris.emplace_back(P::Point_3(a[0],a[1],a[2]),P::Point_3(b[0],b[1],b[2]),P::Point_3(c[0],c[1],c[2]));}CGAL::AABB_tree<Traits> tree(tris.cbegin(),tris.cend());tree.build();
 using Key=std::array<int64_t,3>;std::vector<std::pair<Key,size_t>> order;order.reserve(query.f.size());for(size_t i=0;i<query.f.size();++i){Key key;for(int d=0;d<3;++d){double sum=0;for(auto v:query.f[i])sum+=query.v[v][d];key[d]=std::floor((sum/3)/tile);}order.emplace_back(key,i);}std::sort(order.begin(),order.end());Result result;
 for(size_t begin=0;begin<order.size();){size_t end=begin+1;while(end<order.size()&&order[end].first==order[begin].first)++end;
  for(size_t first=begin;first<end;first+=batch){size_t last=std::min(first+batch,end);std::array<double,3> lo{INFINITY,INFINITY,INFINITY},hi{-INFINITY,-INFINITY,-INFINITY};for(size_t i=first;i<last;++i)for(auto id:query.f[order[i].second])for(int d=0;d<3;++d){lo[d]=std::min(lo[d],query.v[id][d]);hi[d]=std::max(hi[d],query.v[id][d]);}for(int d=0;d<3;++d){lo[d]=std::nextafter(lo[d]-eps,-INFINITY);hi[d]=std::nextafter(hi[d]+eps,INFINITY);}
   std::vector<Iterator> hit;tree.all_intersected_primitives(P::Iso_cuboid_3(lo[0],lo[1],lo[2],hi[0],hi[1],hi[2]),std::back_inserter(hit));++result.groups;result.max_targets=std::max(result.max_targets,hit.size());if(hit.empty())return result;if(hit.size()>100000)throw std::runtime_error("Local envelope exceeds fixed 100000-face resource cap");
   std::unordered_map<uint64_t,size_t> index;std::vector<K::Point_3> points;std::vector<std::array<size_t,3>> faces;faces.reserve(hit.size());
   for(auto it:hit){auto f=target.f[std::distance(tris.cbegin(),it)];std::array<size_t,3> local;for(int j=0;j<3;++j){auto entry=index.emplace(f[j],points.size());if(entry.second){auto p=target.v[f[j]];points.emplace_back(p[0],p[1],p[2]);}local[j]=entry.first->second;}faces.push_back(local);}
   CGAL::Polyhedral_envelope<K> envelope(points,faces,eps);
   for(size_t i=first;i<last;++i){auto f=query.f[order[i].second];auto a=query.v[f[0]],b=query.v[f[1]],c=query.v[f[2]];std::array<K::Point_3,3> query_triangle{K::Point_3(a[0],a[1],a[2]),K::Point_3(b[0],b[1],b[2]),K::Point_3(c[0],c[1],c[2])};if(!envelope(query_triangle[0],query_triangle[1],query_triangle[2])){++result.fallback_queries;if(!exact_cover(query_triangle,tree,K::FT(eps)*K::FT(eps),result.fallback_nodes,result.fallback_leaves))return result;}++result.checked;}
  }begin=end;
 }result.passed=result.checked==query.f.size();return result;
}
int main(int argc,char**argv){if(argc!=7)return 2;auto start=std::chrono::steady_clock::now();std::string error;Result forward,reverse;size_t nf=0,ng=0;double eps=0,tile=0;size_t batch=0;
 try{eps=std::stod(argv[4]);tile=std::stod(argv[5]);batch=std::stoull(argv[6]);if(!(eps>0&&tile>eps&&std::isfinite(eps)&&std::isfinite(tile)&&batch>0&&batch<=4096))throw std::runtime_error("Invalid settings");auto a=read(argv[1]),b=read(argv[2]);nf=a.f.size();ng=b.f.size();forward=direction(a,b,eps,tile,batch);reverse=direction(b,a,eps,tile,batch);if(!forward.passed||!reverse.passed)throw std::runtime_error("Complete triangle envelope membership refused");}catch(const std::exception&e){error=e.what();}
 struct rusage usage{};getrusage(RUSAGE_SELF,&usage);std::ofstream out(argv[3]);out<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"complete_exact_symmetric_distance_passed":"exact_distance_refused")<<"\",\"error\":\""<<error<<"\",\"source_faces\":"<<nf<<",\"candidate_faces\":"<<ng<<",\"source_faces_checked\":"<<forward.checked<<",\"candidate_faces_checked\":"<<reverse.checked<<",\"source_in_candidate_envelope\":"<<forward.passed<<",\"candidate_in_source_envelope\":"<<reverse.passed<<",\"groups\":"<<forward.groups+reverse.groups<<",\"fallback_queries\":"<<forward.fallback_queries+reverse.fallback_queries<<",\"fallback_nodes\":"<<forward.fallback_nodes+reverse.fallback_nodes<<",\"fallback_leaves\":"<<forward.fallback_leaves+reverse.fallback_leaves<<",\"maximum_local_target_faces\":"<<std::max(forward.max_targets,reverse.max_targets)<<",\"tolerance_mm\":"<<eps<<",\"tile_mm\":"<<tile<<",\"batch_faces\":"<<batch<<",\"peak_resident_kib\":"<<usage.ru_maxrss<<",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"certificate\":\"Every complete query triangle passes the conservative polyhedral envelope or an exact adaptive convex-triangle distance certificate. Both full inventories are exhausted on success. Exact midpoint children partition each refused parent. No sampled acceptance. Embedding is separate.\"}\n";return error.empty()?0:2;}
