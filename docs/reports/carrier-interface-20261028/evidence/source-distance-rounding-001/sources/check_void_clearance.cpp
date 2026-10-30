#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_face_graph_triangle_primitive.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/boost/graph/iterator.h>
#include <CGAL/number_utils.h>
#include <CGAL/squared_distance_3.h>
#include <fstream>
#include <iostream>
#include <vector>
#include <limits>
#include <cmath>
#include <iomanip>
#include <stdexcept>
using K=CGAL::Exact_predicates_exact_constructions_kernel;using M=CGAL::Surface_mesh<K::Point_3>;
M read(const char*name){bool binary=std::string(name).find(".meshbin")!=std::string::npos;std::ifstream in(name,binary?std::ios::binary:std::ios::in);uint64_t nv,nf;if(binary){in.read(reinterpret_cast<char*>(&nv),8);in.read(reinterpret_cast<char*>(&nf),8);}else in>>nv>>nf;if(!in)throw std::runtime_error("Missing source");M m;std::vector<M::Vertex_index>v;v.reserve(nv);for(uint64_t i=0;i<nv;++i){double p[3];if(binary)in.read(reinterpret_cast<char*>(p),24);else in>>p[0]>>p[1]>>p[2];v.push_back(m.add_vertex(K::Point_3(p[0],p[1],p[2])));}for(uint64_t i=0;i<nf;++i){uint64_t p[3];if(binary)in.read(reinterpret_cast<char*>(p),24);else in>>p[0]>>p[1]>>p[2];if(!in||p[0]>=nv||p[1]>=nv||p[2]>=nv||m.add_face(v[p[0]],v[p[1]],v[p[2]])==M::null_face())throw std::runtime_error("Invalid indexed face");}if(!CGAL::is_closed(m)||!CGAL::is_valid_polygon_mesh(m))throw std::runtime_error("Closed valid surface required");return m;}
int main(int argc,char**argv){if(argc!=4)return 2;try{M a=read(argv[1]),b=read(argv[2]);using Primitive=CGAL::AABB_face_graph_triangle_primitive<M>;using Traits=CGAL::AABB_traits<K,Primitive>;CGAL::AABB_tree<Traits>tree(faces(a).first,faces(a).second,a);tree.accelerate_distance_queries();double lower=std::numeric_limits<double>::infinity(),worst_center=0,worst_cover=0;size_t count=0,worst=0;for(auto fi:b.faces()){std::vector<K::Point_3>v;for(auto vi:CGAL::vertices_around_face(b.halfedge(fi),b))v.push_back(b.point(vi));K::Point_3 center((v[0].x()+v[1].x()+v[2].x())/3,(v[0].y()+v[1].y()+v[2].y())/3,(v[0].z()+v[1].z()+v[2].z())/3);auto d2=tree.squared_distance(center);K::FT radius2=0;for(const auto&p:v)radius2=CGAL::max(radius2,CGAL::squared_distance(center,p));auto di=CGAL::to_interval(CGAL::exact(d2)),ri=CGAL::to_interval(CGAL::exact(radius2));double dl=std::nextafter(std::sqrt(std::max(0.,di.first)),-std::numeric_limits<double>::infinity()),ru=std::nextafter(std::sqrt(ri.second),std::numeric_limits<double>::infinity());double bound=std::nextafter(dl-ru,-std::numeric_limits<double>::infinity());if(bound<lower){lower=bound;worst=fi.idx();worst_center=dl;worst_cover=ru;}++count;}bool passed=lower>.125;std::ofstream out(argv[3]);out<<std::setprecision(17)<<"{\"status\":\""<<(passed?"complete_clearance_budget_passed":"clearance_budget_refused")<<"\",\"faces_checked\":"<<count<<",\"minimum_complete_clearance_lower_mm\":"<<lower<<",\"required_clearance_mm\":0.125,\"worst_face\":"<<worst<<",\"worst_centroid_distance_lower_mm\":"<<worst_center<<",\"worst_face_cover_radius_upper_mm\":"<<worst_cover<<",\"method\":\"Exact source nearest distance at each exact centroid, minus outward interval radius covering the entire triangle; distance is 1-Lipschitz\",\"manufacturing_authorized\":false}\n";std::cout<<"All-face clearance lower "<<lower<<"mm"<<std::endl;return passed?0:2;}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 2;}}
