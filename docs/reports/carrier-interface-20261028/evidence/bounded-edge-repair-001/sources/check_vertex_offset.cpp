#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/AABB_face_graph_triangle_primitive.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_tree.h>
#include <fstream>
#include <vector>
#include <iostream>
#include <stdexcept>
#include <cstdint>
#include <cmath>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using M=CGAL::Surface_mesh<K::Point_3>;
using P=CGAL::AABB_face_graph_triangle_primitive<M>;
using T=CGAL::AABB_traits<K,P>;
int main(int argc,char**argv){
  if(argc!=4)return 2;
  bool before=false,after=false,dot=false,radius=false;std::string error;uint64_t nf=0;
  try{
    std::ifstream in(argv[1],std::ios::binary);uint64_t nv=0;in.read((char*)&nv,8);in.read((char*)&nf,8);
    if(!in||nv>20000000||nf>40000000)throw std::runtime_error("Invalid source header");
    M mesh;std::vector<M::Vertex_index>ids;std::vector<K::Point_3>points;
    for(uint64_t i=0;i<nv;++i){double p[3];in.read((char*)p,24);if(!in||!std::isfinite(p[0])||!std::isfinite(p[1])||!std::isfinite(p[2]))throw std::runtime_error("Invalid point");points.emplace_back(p[0],p[1],p[2]);ids.push_back(mesh.add_vertex(points.back()));}
    for(uint64_t i=0;i<nf;++i){uint64_t p[3];in.read((char*)p,24);if(!in||p[0]>=nv||p[1]>=nv||p[2]>=nv||mesh.add_face(ids[p[0]],ids[p[1]],ids[p[2]])==M::null_face())throw std::runtime_error("Invalid face");}
    std::ifstream q(argv[2]);uint64_t vi;double a[3],b[3];q>>vi>>a[0]>>a[1]>>a[2]>>b[0]>>b[1]>>b[2];if(!q||vi>=nv)throw std::runtime_error("Invalid queries");
    K::Point_3 x(a[0],a[1],a[2]),y(b[0],b[1],b[2]),c=points[vi];
    CGAL::AABB_tree<T>tree(faces(mesh).first,faces(mesh).second,mesh);tree.accelerate_distance_queries();
    before=tree.closest_point(x)==c;after=tree.closest_point(y)==c;
    dot=(x-c)*(y-c)>K::FT(0);
    K::FT r=K::FT(1)/10,e=K::FT(1)/1000000000;
    K::FT d=CGAL::squared_distance(y,c);radius=d>=(r-e)*(r-e)&&d<=(r+e)*(r+e);
    if(!before||!after||!dot||!radius)throw std::runtime_error("Nearest-vertex offset conditions refused");
  }catch(const std::exception&e){error=e.what();}
  std::ofstream o(argv[3]);o<<"{\"status\":\""<<(error.empty()?"exact_nearest_vertex_offset_passed":"nearest_vertex_offset_refused")<<"\",\"error\":\""<<error<<"\",\"source_faces\":"<<nf<<",\"before_exact_nearest_vertex\":"<<(before?"true":"false")<<",\"after_exact_nearest_vertex\":"<<(after?"true":"false")<<",\"endpoint_vectors_exact_dot_positive\":"<<(dot?"true":"false")<<",\"after_distance_in_exact_radius_interval\":"<<(radius?"true":"false")<<",\"radius_mm\":0.1,\"radius_interval_halfwidth_mm\":1e-9,\"manufacturing_authorized\":false}\n";
  std::cout<<(error.empty()?"PASS":"REFUSED")<<" "<<error<<std::endl;return error.empty()?0:2;
}
