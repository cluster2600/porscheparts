// Exact closed-volume clipping. Hypothetical cut planes are supplied privately.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/clip.h>
#include <CGAL/Polygon_mesh_processing/triangulate_faces.h>
#include <CGAL/boost/graph/helpers.h>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<K::Point_3>;
namespace PMP=CGAL::Polygon_mesh_processing;

template<class T> std::vector<T> read(const std::string& path,size_t count) {
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    if(!in || in.tellg()!=std::streamoff(count*sizeof(T))) throw std::runtime_error("Binary input length mismatch");
    in.seekg(0);std::vector<T> data(count);
    if(!in.read(reinterpret_cast<char*>(data.data()),data.size()*sizeof(T))) throw std::runtime_error("Binary input read failed");
    return data;
}

int main(int argc,char** argv) {
    try {
        if(argc!=7) throw std::runtime_error("Usage: clip-head VERTICES_F64LE FACES_I64LE Nv Nf PLANES_TXT NEW_OUTPUT");
        size_t nv=std::stoull(argv[3]),nf=std::stoull(argv[4]);
        if(!nv || !nf) throw std::runtime_error("Empty input");
        if(std::filesystem::exists(argv[6])) throw std::runtime_error("Existing output refused");
        auto vertices=read<double>(argv[1],nv*3);auto faces=read<int64_t>(argv[2],nf*3);
        std::ifstream planes_file(argv[5]);size_t count=0;
        if(!(planes_file>>count) || !count || count>16) throw std::runtime_error("Invalid plane count");
        std::vector<std::array<double,4>> planes(count);
        for(auto& p:planes) {
            for(double& x:p) if(!(planes_file>>x) || !std::isfinite(x)) throw std::runtime_error("Invalid plane coefficient");
            if(p[0]*p[0]+p[1]*p[1]+p[2]*p[2]==0) throw std::runtime_error("Zero plane normal");
        }
        Mesh mesh;mesh.reserve(nv,3*nf/2,nf);
        std::vector<Mesh::Vertex_index> ids;ids.reserve(nv);
        for(size_t i=0;i<nv;++i) {
            for(size_t j=0;j<3;++j) if(!std::isfinite(vertices[3*i+j])) throw std::runtime_error("Nonfinite coordinate");
            ids.push_back(mesh.add_vertex(K::Point_3(vertices[3*i],vertices[3*i+1],vertices[3*i+2])));
        }
        for(size_t i=0;i<nf;++i) {
            for(size_t j=0;j<3;++j) if(faces[3*i+j]<0 || size_t(faces[3*i+j])>=nv) throw std::runtime_error("Invalid face index");
            if(mesh.add_face(ids[faces[3*i]],ids[faces[3*i+1]],ids[faces[3*i+2]])==Mesh::null_face()) throw std::runtime_error("Invalid indexed input topology");
        }
        vertices.clear();vertices.shrink_to_fit();faces.clear();faces.shrink_to_fit();ids.clear();ids.shrink_to_fit();
        if(!CGAL::is_closed(mesh) || !CGAL::is_triangle_mesh(mesh)) throw std::runtime_error("Input is not a closed triangle mesh");
        std::cerr<<"INPUT_READY "<<mesh.number_of_vertices()<<" "<<mesh.number_of_faces()<<std::endl;
        for(size_t i=0;i<planes.size();++i) {
            auto p=planes[i];
            bool ok=PMP::clip(mesh,K::Plane_3(p[0],p[1],p[2],p[3]),CGAL::parameters::clip_volume(true));
            if(!ok || mesh.is_empty() || !CGAL::is_closed(mesh)) throw std::runtime_error("Closed-volume clipping refused or empty");
            std::cerr<<"PLANE_DONE "<<i<<" "<<mesh.number_of_faces()<<std::endl;
        }
        if(!PMP::triangulate_faces(mesh) || !CGAL::is_closed(mesh) || !CGAL::is_triangle_mesh(mesh)) throw std::runtime_error("Closed triangulated output unavailable");
        mesh.collect_garbage();
        auto out=std::filesystem::path(argv[6]);std::filesystem::create_directories(out);
        std::ofstream vo(out/"vertices.f64le",std::ios::binary),fo(out/"faces.i64le",std::ios::binary);
        auto map=mesh.add_property_map<Mesh::Vertex_index,int64_t>("v:export",-1).first;int64_t serial=0;
        for(auto v:mesh.vertices()) {
            map[v]=serial++;auto p=mesh.point(v);double xyz[3]={CGAL::to_double(p.x()),CGAL::to_double(p.y()),CGAL::to_double(p.z())};
            vo.write(reinterpret_cast<char*>(xyz),sizeof(xyz));
        }
        for(auto f:mesh.faces()) {
            int64_t triangle[3];int j=0;
            for(auto v:CGAL::vertices_around_face(mesh.halfedge(f),mesh)) {
                if(j>=3) throw std::runtime_error("Nontriangular output face");triangle[j++]=map[v];
            }
            if(j!=3) throw std::runtime_error("Incomplete output face");
            fo.write(reinterpret_cast<char*>(triangle),sizeof(triangle));
        }
        if(!vo || !fo) throw std::runtime_error("Output write failed");
        std::ofstream meta(out/"native.json");
        meta<<"{\"vertices\":"<<mesh.number_of_vertices()<<",\"triangles\":"<<mesh.number_of_faces()<<",\"closed\":true,\"hypothetical_closures\":true,\"physical_acceptance\":false}\n";
        std::cout<<"CLOSED_HYPOTHESIS_CANDIDATE_WRITTEN"<<std::endl;
    } catch(const std::exception& e) {std::cerr<<e.what()<<std::endl;return 1;}
}
