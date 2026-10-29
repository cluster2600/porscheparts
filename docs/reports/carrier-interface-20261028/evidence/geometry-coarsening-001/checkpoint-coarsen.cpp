#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/Surface_mesh_simplification/edge_collapse.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Edge_count_stop_predicate.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/LindstromTurk_cost.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/LindstromTurk_placement.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Bounded_normal_change_filter.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/FastEnvelope_filter.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <sys/resource.h>
#include <memory>
using K=CGAL::Exact_predicates_inexact_constructions_kernel;
using M=CGAL::Surface_mesh<K::Point_3>;
namespace SMS=CGAL::Surface_mesh_simplification;
struct StopState {bool checkpoint=false;bool target=false;};
struct CheckpointStop {
 std::size_t threshold;std::chrono::steady_clock::time_point deadline;std::shared_ptr<StopState> state;
 template<class Cost,class Profile> bool operator()(const Cost&,const Profile&,std::size_t,std::size_t current)const{
  if(current<threshold){state->target=true;return true;}
  if(std::chrono::steady_clock::now()>=deadline){state->checkpoint=true;return true;}
  return false;
 }
};
int main(int argc,char**argv){
  if(argc!=7)return 2;
  auto start=std::chrono::steady_clock::now();std::string error;uint64_t nv=0,nf=0,outv=0,outf=0;std::size_t collapsed=0;
  double epsilon=0,ratio=0,soft_seconds=0;auto state=std::make_shared<StopState>();
  try{
    epsilon=std::stod(argv[4]);ratio=std::stod(argv[5]);soft_seconds=std::stod(argv[6]);
    if(!std::isfinite(soft_seconds)||soft_seconds<0)throw std::runtime_error("Invalid checkpoint duration");
    if(!(epsilon>0&&std::isfinite(epsilon)&&ratio>0&&ratio<1))throw std::runtime_error("Invalid fixed coarsening settings");
    if(std::filesystem::exists(argv[2])||std::filesystem::exists(argv[3]))throw std::runtime_error("Fresh outputs required");
    std::ifstream in(argv[1],std::ios::binary);in.read((char*)&nv,8);in.read((char*)&nf,8);
    if(!in||nv>20000000||nf>40000000)throw std::runtime_error("Invalid input header");
    M mesh;std::vector<M::Vertex_index>vertices;vertices.reserve(nv);
    for(uint64_t i=0;i<nv;++i){double p[3];in.read((char*)p,24);if(!in||!std::isfinite(p[0])||!std::isfinite(p[1])||!std::isfinite(p[2]))throw std::runtime_error("Invalid point");vertices.push_back(mesh.add_vertex(K::Point_3(p[0],p[1],p[2])));}
    for(uint64_t i=0;i<nf;++i){uint64_t f[3];in.read((char*)f,24);if(!in||f[0]>=nv||f[1]>=nv||f[2]>=nv||mesh.add_face(vertices[f[0]],vertices[f[1]],vertices[f[2]])==M::null_face())throw std::runtime_error("Invalid face");}
    if(!CGAL::is_valid_polygon_mesh(mesh)||!CGAL::is_closed(mesh)||!CGAL::is_triangle_mesh(mesh))throw std::runtime_error("Closed valid triangular input required");
    std::cout<<"INPUT_LOADED "<<nv<<" "<<nf<<std::endl;
    using Filter=SMS::FastEnvelope_filter<K,SMS::Bounded_normal_change_filter<>>;
    Filter filter(epsilon);
    CheckpointStop stop{std::max<std::size_t>(1,std::ceil(mesh.number_of_edges()*ratio)),start+std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(soft_seconds)),state};
    collapsed=SMS::edge_collapse(mesh,stop,CGAL::parameters::get_cost(SMS::LindstromTurk_cost<M>()).filter(filter).get_placement(SMS::LindstromTurk_placement<M>()));
    mesh.collect_garbage();
    if(!CGAL::is_valid_polygon_mesh(mesh)||!CGAL::is_closed(mesh)||!CGAL::is_triangle_mesh(mesh))throw std::runtime_error("Closed triangular output required");
    outv=mesh.number_of_vertices();outf=mesh.number_of_faces();
    std::ofstream out(argv[2],std::ios::binary);out.write((char*)&outv,8);out.write((char*)&outf,8);
    for(auto v:mesh.vertices()){auto p=mesh.point(v);double q[3]={p.x(),p.y(),p.z()};if(!std::isfinite(q[0])||!std::isfinite(q[1])||!std::isfinite(q[2]))throw std::runtime_error("Nonfinite output");out.write((char*)q,24);}
    for(auto f:mesh.faces()){uint64_t q[3];int i=0;for(auto v:CGAL::vertices_around_face(mesh.halfedge(f),mesh)){if(i==3)throw std::runtime_error("Nontriangle");q[i++]=v.idx();}if(i!=3)throw std::runtime_error("Nontriangle");out.write((char*)q,24);}
    if(!out)throw std::runtime_error("Incomplete output write");
  }catch(const std::exception&e){error=e.what();}
  double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
  std::ofstream report(argv[3]);report<<std::setprecision(17)<<"{\"status\":\""<<(error.empty()?"checkpoint_candidate_independent_checks_pending":"coarsening_refused")<<"\",\"error\":\""<<error<<"\",\"source_vertices\":"<<nv<<",\"source_faces\":"<<nf<<",\"output_vertices\":"<<outv<<",\"output_faces\":"<<outf<<",\"removed_edges\":"<<collapsed<<",\"envelope_mm\":"<<epsilon<<",\"target_remaining_edge_ratio\":"<<ratio<<",\"elapsed_seconds\":"<<elapsed<<",\"peak_resident_kib\":"<<usage.ru_maxrss<<",\"kernel\":\"CGAL5.6 EPICK + FastEnvelope\",\"symmetric_fidelity_certified\":false,\"embedding_certified\":false,\"manufacturing_authorized\":false}\n";
  std::ofstream receipt(std::string(argv[3])+".checkpoint.json");receipt<<"{\"soft_limit_seconds\":"<<soft_seconds<<",\"checkpoint_reached\":"<<(state->checkpoint?"true":"false")<<",\"target_reached\":"<<(state->target?"true":"false")<<",\"source_envelope_fixed_for_this_run\":true,\"continuation_against_new_source_authorized\":false}\n";
  std::cout<<(error.empty()?"GENERATED":"REFUSED")<<" "<<outf<<" "<<error<<std::endl;return error.empty()?0:2;
}
