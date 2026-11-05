// Exact-decimal layer planes, with explicit zero-material tangent handling.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_slicer.h>
#include <CGAL/boost/graph/helpers.h>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<K::Point_3>;

template<class T>std::vector<T> read(const char* path,size_t n){
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    if(!in || in.tellg()!=std::streamoff(n*sizeof(T)))throw std::runtime_error("Input size mismatch");
    in.seekg(0);std::vector<T> result(n);
    if(!in.read(reinterpret_cast<char*>(result.data()),n*sizeof(T)))throw std::runtime_error("Input read failed");
    return result;
}

bool line_only(const std::vector<K::Point_3>& p){
    if(p.size()<3)return true;
    size_t next=1;while(next<p.size() && p[next]==p[0])++next;
    if(next==p.size())return true;
    for(auto q:p)if(!CGAL::collinear(p[0],p[next],q))return false;
    return true;
}

int main(int argc,char** argv){
    try{
        if(argc!=8)throw std::runtime_error("Usage: slice-hypothesis VERT_F64LE FACES_I64LE Nv Nf DECIMAL_LAYER_MM NEW_CLI NEW_JSON");
        if(std::ifstream(argv[6]).good() || std::ifstream(argv[7]).good())throw std::runtime_error("Existing output refused");
        std::string text=argv[5];auto dot=text.find('.');
        if(dot==std::string::npos || text.substr(0,dot)!="0" || text.size()-dot-1>6)throw std::runtime_error("Use an exact decimal layer between zero and one mm");
        long denominator=1;for(size_t i=dot+1;i<text.size();++i)denominator*=10;
        long numerator=std::stol(text.substr(dot+1));
        if(numerator<=0 || numerator>=denominator)throw std::runtime_error("Invalid layer height");
        K::FT dz=K::FT(numerator)/K::FT(denominator);double layer_mm=CGAL::to_double(dz);
        auto start=std::chrono::steady_clock::now();size_t nv=std::stoull(argv[3]),nf=std::stoull(argv[4]);
        auto v=read<double>(argv[1],nv*3);auto f=read<int64_t>(argv[2],nf*3);
        Mesh mesh;mesh.reserve(nv,3*nf/2,nf);std::vector<Mesh::Vertex_index> ids;ids.reserve(nv);
        for(size_t i=0;i<nv;++i)ids.push_back(mesh.add_vertex(K::Point_3(v[3*i],v[3*i+1],v[3*i+2])));
        for(size_t i=0;i<nf;++i){
            for(int j=0;j<3;++j)if(f[3*i+j]<0 || size_t(f[3*i+j])>=nv)throw std::runtime_error("Invalid index");
            if(mesh.add_face(ids[f[3*i]],ids[f[3*i+1]],ids[f[3*i+2]])==Mesh::null_face())throw std::runtime_error("Invalid face topology");
        }
        if(!CGAL::is_closed(mesh) || !CGAL::is_triangle_mesh(mesh))throw std::runtime_error("Closed triangle mesh required");
        K::FT highest=0;for(auto vertex:mesh.vertices()){
            auto z=mesh.point(vertex).z();if(z<0)throw std::runtime_error("Geometry below slicing origin");highest=std::max(highest,z);
        }
        v.clear();v.shrink_to_fit();f.clear();f.shrink_to_fit();ids.clear();ids.shrink_to_fit();
        int layers=static_cast<int>(std::ceil(CGAL::to_double(highest/dz)));
        CGAL::Polygon_mesh_slicer<Mesh,K> slicer(mesh);
        std::ofstream out(argv[6]);out<<std::setprecision(17);
        out<<"$$HEADERSTART\n$$ASCII\n$$UNITS/1.0\n$$VERSION/200\n$$LABEL/1,\"935 local-cut hypothesis - machine qualification pending\"\n$$LAYERS/"<<layers+1<<"\n$$HEADEREND\n$$GEOMETRYSTART\n$$LAYER/0\n";
        size_t contours=0,coordinates=0,tangencies=0;long double integrated=0;
        for(int layer=1;layer<=layers;++layer){
            K::FT z=K::FT(layer)*dz,area_sum=0;std::vector<std::vector<K::Point_3>> loops;
            slicer(K::Plane_3(0,0,1,-z),std::back_inserter(loops));out<<"$$LAYER/"<<CGAL::to_double(z)<<'\n';
            for(auto& loop:loops){
                if(line_only(loop)){++tangencies;continue;}
                if(loop.size()<4 || loop.front()!=loop.back())throw std::runtime_error("Non-closed material section");
                K::FT twice=0;auto origin=loop.front();
                for(size_t i=1;i<loop.size();++i)twice+=(loop[i-1].x()-origin.x())*(loop[i].y()-origin.y())-(loop[i].x()-origin.x())*(loop[i-1].y()-origin.y());
                if(twice==0)throw std::runtime_error("Non-collinear zero-area section");
                area_sum+=twice/2;out<<"$$POLYLINE/1,"<<(twice>0?1:0)<<','<<loop.size();
                for(auto point:loop)out<<','<<CGAL::to_double(point.x())<<','<<CGAL::to_double(point.y());
                out<<'\n';++contours;coordinates+=loop.size();
            }
            integrated+=CGAL::to_double(area_sum)*layer_mm;
            if(layer%100==0){out.flush();std::cerr<<"LAYER_DONE "<<layer<<'/'<<layers<<" contours="<<contours<<std::endl;}
        }
        out<<"$$GEOMETRYEND\n";out.close();if(!out)throw std::runtime_error("CLI write failed");
        std::ofstream report(argv[7]);report<<std::setprecision(17)<<"{\"layers\":"<<layers<<",\"layer_mm\":"<<layer_mm<<",\"exact_decimal_layer\":true,\"contours\":"<<contours<<",\"coordinate_pairs\":"<<coordinates<<",\"exact_collinear_tangent_sections_skipped\":"<<tangencies<<",\"right_endpoint_volume_mm3\":"<<static_cast<double>(integrated)<<",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"machine_job\":false,\"manufacturing_qualified\":false}\n";
    }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
