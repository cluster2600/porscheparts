// Separate cap-only codec adapter; exact source blocks and two open-cap codec substitutions are recorded.
#pragma once
// Separate analysis candidate only: original-source local quality remeshing.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/remesh.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_face_graph_triangle_primitive.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

using Kernel=CGAL::Exact_predicates_inexact_constructions_kernel;
using Point=Kernel::Point_3;
using Mesh=CGAL::Surface_mesh<Point>;
using Vertex=Mesh::Vertex_index;
using Face=Mesh::Face_index;
using Primitive=CGAL::AABB_face_graph_triangle_primitive<Mesh>;
using Tree=CGAL::AABB_tree<CGAL::AABB_traits<Kernel,Primitive>>;
namespace PMP=CGAL::Polygon_mesh_processing;
namespace fs=std::filesystem;

template<class T> T read_value(std::istream& input) {
  T value;
  if(!input.read(reinterpret_cast<char*>(&value),sizeof(value)))
    throw std::runtime_error("Incomplete indexed surface");
  return value;
}
template<class T> void write_value(std::ostream& out,T value) {
  out.write(reinterpret_cast<const char*>(&value),sizeof(value));
}
std::array<Vertex,3> vertices(const Mesh& mesh,Face face) {
  auto h=mesh.halfedge(face);
  return {mesh.source(h),mesh.target(h),mesh.target(mesh.next(h))};
}
std::array<std::size_t,3> canonical_face(const Mesh& mesh,Face face) {
  auto v=vertices(mesh,face);
  std::array<std::size_t,3> best={v[0].idx(),v[1].idx(),v[2].idx()};
  for(int i=1;i<3;++i) {
    std::array<std::size_t,3> row={v[i].idx(),v[(i+1)%3].idx(),v[(i+2)%3].idx()};
    if(row<best)best=row;
  }
  return best;
}
Mesh read_surface(const fs::path& path) {
  std::ifstream in(path,std::ios::binary);char magic[8];
  if(!in.read(magic,8)||std::memcmp(magic,"962SURF1",8))
    throw std::runtime_error("Expected binary64/uint64 indexed surface");
  auto nv=read_value<std::uint64_t>(in),nf=read_value<std::uint64_t>(in);
  if(!nv||!nf||nv>2000000||nf>2000000||fs::file_size(path)!=24+24*(nv+nf))
    throw std::runtime_error("Invalid indexed surface counts");
  Mesh mesh;mesh.reserve(nv,3*nf/2,nf);std::vector<Vertex> ids;ids.reserve(nv);
  for(std::uint64_t i=0;i<nv;++i) {
    double x=read_value<double>(in),y=read_value<double>(in),z=read_value<double>(in);
    if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))
      throw std::runtime_error("Nonfinite source point");
    ids.push_back(mesh.add_vertex(Point(x,y,z)));
  }
  for(std::uint64_t i=0;i<nf;++i) {
    auto a=read_value<std::uint64_t>(in),b=read_value<std::uint64_t>(in),c=read_value<std::uint64_t>(in);
    if(a>=nv||b>=nv||c>=nv||a==b||b==c||c==a
       ||CGAL::collinear(mesh.point(ids[a]),mesh.point(ids[b]),mesh.point(ids[c]))
       ||mesh.add_face(ids[a],ids[b],ids[c])==Mesh::null_face())
      throw std::runtime_error("Invalid source triangle");
  }
  if(!CGAL::is_triangle_mesh(mesh)||!CGAL::is_valid_polygon_mesh(mesh))
    throw std::runtime_error("Valid oriented triangular cap source required");
  return mesh;
}
void write_surface(const Mesh& mesh,const fs::path& path) {
  if(fs::exists(path)||fs::is_symlink(path))throw std::runtime_error("Existing output preserved");
  std::ofstream out(path,std::ios::binary);out.write("962SURF1",8);
  write_value<std::uint64_t>(out,mesh.number_of_vertices());
  write_value<std::uint64_t>(out,mesh.number_of_faces());
  std::vector<std::uint64_t> ids(mesh.num_vertices(),std::uint64_t(-1));
  std::uint64_t i=0;
  for(auto v:mesh.vertices()) {
    ids[v.idx()]=i++;auto p=mesh.point(v);
    write_value<double>(out,p.x());write_value<double>(out,p.y());write_value<double>(out,p.z());
  }
  for(auto f:mesh.faces())for(auto v:vertices(mesh,f))write_value<std::uint64_t>(out,ids[v.idx()]);
  out.close();if(!out)throw std::runtime_error("Surface output failed");
}
double triangle_quality(const Mesh& mesh,Face f) {
  auto v=vertices(mesh,f);auto u=mesh.point(v[1])-mesh.point(v[0]);auto w=mesh.point(v[2])-mesh.point(v[0]);
  double sum=u.squared_length()+w.squared_length()+(w-u).squared_length();
  return 2*std::sqrt(3.0)*std::sqrt(CGAL::cross_product(u,w).squared_length())/sum;
}
struct Quality { std::size_t faces=0,bad=0;double minimum=1; };
Quality quality(const Mesh& mesh) {
  Quality result;
  for(auto f:mesh.faces()) {
    double q=triangle_quality(mesh,f);
    if(!std::isfinite(q)||q<0)throw std::runtime_error("Nonfinite triangle quality");
    ++result.faces;result.bad+=q<2.0/29.0;result.minimum=std::min(result.minimum,q);
  }
  return result;
}
std::string json_quality(const Quality& q) {
  std::ostringstream s;s<<std::setprecision(17)<<"{\"triangles\":"<<q.faces
    <<",\"below_necessary_bound\":"<<q.bad<<",\"minimum_triangle_SICN\":"<<q.minimum<<"}";
  return s.str();
}

#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_2.h>
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
using Chain=std::map<Edge,long>;
void chain_add(Chain& c,Row t) {
  for(int i=0;i<3;++i) {auto a=t[i],b=t[(i+1)%3];Edge e{std::min(a,b),std::max(a,b)};c[e]+=a<b?1:-1;if(!c[e])c.erase(e);}
}
using Exact=CGAL::Exact_predicates_exact_constructions_kernel;
using P2=Exact::Point_2;
using FT=Exact::FT;
using Polygon=CGAL::Polygon_2<Exact>;
struct Complex {
  bool valid=false;std::size_t vertices=0,edges=0,faces=0,components=0;long long euler=0;
  Chain boundary;std::vector<std::vector<std::size_t>> loops;
};
Complex complex(const std::vector<Row>& rows) {
  Complex c;c.faces=rows.size();if(rows.empty())return c;
  std::map<Edge,std::vector<std::pair<std::size_t,int>>> edges;
  std::map<std::size_t,std::vector<Edge>> links;UF face_groups(rows.size());
  for(std::size_t i=0;i<rows.size();++i)for(int j=0;j<3;++j) {
    auto a=rows[i][j],b=rows[i][(j+1)%3],d=rows[i][(j+2)%3];
    if(a==b||a==d||b==d)return c;
    edges[std::minmax(a,b)].push_back({i,a<b?1:-1});links[a].push_back(std::minmax(b,d));
  }
  std::map<std::size_t,std::size_t> next;std::map<std::size_t,int> incoming;
  for(const auto& e:edges) {
    if(e.second.size()==2) {if(e.second[0].second+e.second[1].second)return c;face_groups.join(e.second[0].first,e.second[1].first);}
    else if(e.second.size()==1) {
      auto a=e.first.first,b=e.first.second;if(e.second[0].second<0)std::swap(a,b);
      if(!next.emplace(a,b).second||++incoming[b]!=1)return c;
      c.boundary[e.first]=e.second[0].second;
    }else return c;
  }
  if(next.size()!=incoming.size())return c;
  for(const auto& x:next)if(!incoming.count(x.first))return c;
  for(const auto& x:links) {
    std::map<std::size_t,std::vector<std::size_t>> graph;std::set<Edge> unique;
    for(auto e:x.second) {if(!unique.insert(e).second)return c;graph[e.first].push_back(e.second);graph[e.second].push_back(e.first);}
    std::set<std::size_t> unseen;for(const auto& y:graph)unseen.insert(y.first);
    std::vector<std::size_t> pending{*unseen.begin()};unseen.erase(pending[0]);
    while(!pending.empty()) {auto v=pending.back();pending.pop_back();for(auto w:graph[v])if(unseen.erase(w))pending.push_back(w);}
    if(!unseen.empty())return c;std::size_t ends=0;
    for(const auto& y:graph) {ends+=y.second.size()==1;if(y.second.size()!=1&&y.second.size()!=2)return c;}
    if(next.count(x.first)?ends!=2:ends!=0)return c;
  }
  std::set<std::size_t> todo;for(const auto& x:next)todo.insert(x.first);
  while(!todo.empty()) {
    auto first=*todo.begin(),v=first;std::vector<std::size_t> loop;
    do {if(!todo.erase(v))return c;loop.push_back(v);v=next.at(v);}while(v!=first);
    c.loops.push_back(loop);
  }
  for(std::size_t i=0;i<rows.size();++i)c.components+=face_groups.find(i)==i;
  c.vertices=links.size();c.edges=edges.size();c.euler=static_cast<long long>(c.vertices)-static_cast<long long>(c.edges)+static_cast<long long>(c.faces);c.valid=true;return c;
}
P2 xy(const Point& p) {return P2(p.x(),p.y());}
FT cross2(const P2& a,const P2& b,const P2& c) {return (b.x()-a.x())*(c.y()-a.y())-(b.y()-a.y())*(c.x()-a.x());}
std::string exact_text(const FT& value) {std::ostringstream s;s<<CGAL::exact(value);return s.str();}
std::string quoted(const std::string& value) {
  std::ostringstream s;s<<'"';for(unsigned char c:value) {
    if(c=='"'||c=='\\')s<<'\\'<<c;else if(c<32)s<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;else s<<c;
  }s<<'"';return s.str();
}
template<class T> void list(std::ostream& s,const std::vector<T>& ids) {s<<'[';bool comma=false;for(auto v:ids){if(comma)s<<',';comma=true;s<<v;}s<<']';}
