// Independent native indexed-topology/volume check; no CGAL or model dependency.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <vector>
struct Edge{uint64_t key;uint32_t face;bool forward;};
struct Sets{
    std::vector<uint32_t> parent;
    explicit Sets(size_t n):parent(n){std::iota(parent.begin(),parent.end(),0);}
    uint32_t root(uint32_t x){while(parent[x]!=x){parent[x]=parent[parent[x]];x=parent[x];}return x;}
    void join(uint32_t a,uint32_t b){a=root(a);b=root(b);if(a!=b)parent[std::max(a,b)]=std::min(a,b);}
};
template<class T>std::vector<T> read(const char* path,size_t n){
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    if(!in || in.tellg()!=std::streamoff(n*sizeof(T)))throw std::runtime_error("Input byte count mismatch");
    in.seekg(0);std::vector<T> result(n);
    if(!in.read(reinterpret_cast<char*>(result.data()),n*sizeof(T)))throw std::runtime_error("Input read failed");
    return result;
}
int main(int argc,char** argv){
    try{
        if(argc!=6)throw std::runtime_error("Usage: check-indexed VERT_F64LE FACES_I64LE Nv Nf NEW_JSON");
        if(std::ifstream(argv[5]).good())throw std::runtime_error("Existing output refused");
        size_t nv=std::stoull(argv[3]),nf=std::stoull(argv[4]);
        if(!nv || !nf || nv>UINT32_MAX || nf>UINT32_MAX)throw std::runtime_error("Unsupported dimensions");
        auto v=read<double>(argv[1],nv*3);auto f=read<int64_t>(argv[2],nf*3);
        for(double x:v)if(!std::isfinite(x))throw std::runtime_error("Nonfinite coordinate");
        std::vector<Edge> edges;edges.reserve(3*nf);std::vector<bool> used(nv,false);Sets components(nf);
        long double volume=0;size_t zero=0;
        for(size_t i=0;i<nf;++i){
            std::array<uint32_t,3> ids;
            for(int j=0;j<3;++j){auto index=f[3*i+j];if(index<0 || size_t(index)>=nv)throw std::runtime_error("Invalid index");ids[j]=uint32_t(index);used[index]=true;}
            if(ids[0]==ids[1] || ids[1]==ids[2] || ids[2]==ids[0])throw std::runtime_error("Repeated face corner");
            std::array<long double,3> a,b,c,ab,ac,cross;
            for(int j=0;j<3;++j){a[j]=v[3*ids[0]+j]-v[j];b[j]=v[3*ids[1]+j]-v[j];c[j]=v[3*ids[2]+j]-v[j];ab[j]=b[j]-a[j];ac[j]=c[j]-a[j];}
            cross={ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]};
            zero+=(cross[0]==0 && cross[1]==0 && cross[2]==0);
            volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6;
            for(int j=0;j<3;++j){uint32_t a=ids[j],b=ids[(j+1)%3];edges.push_back({(uint64_t(std::min(a,b))<<32)|std::max(a,b),uint32_t(i),a<b});}
        }
        std::sort(edges.begin(),edges.end(),[](const Edge& a,const Edge& b){return a.key<b.key;});
        size_t open=0,nonmanifold=0,winding=0,unique=0;
        for(size_t i=0;i<edges.size();){size_t end=i+1;while(end<edges.size() && edges[end].key==edges[i].key)++end;++unique;
            if(end-i==1)++open;
            else if(end-i!=2)++nonmanifold;
            else{winding+=edges[i].forward==edges[i+1].forward;components.join(edges[i].face,edges[i+1].face);}
            i=end;
        }
        size_t count=0;for(size_t i=0;i<nf;++i)count+=components.root(uint32_t(i))==i;
        size_t unused=std::count(used.begin(),used.end(),false);
        bool passed=!zero && !open && !nonmanifold && !winding && !unused && count==1 && volume>0;
        std::ofstream out(argv[5]);out.precision(17);
        out<<"{\"vertices\":"<<nv<<",\"triangles\":"<<nf<<",\"unique_edges\":"<<unique<<",\"open_edges\":"<<open<<",\"nonmanifold_edges\":"<<nonmanifold<<",\"inconsistently_oriented_edges\":"<<winding<<",\"zero_area_faces\":"<<zero<<",\"unused_vertices\":"<<unused<<",\"edge_connected_face_components\":"<<count<<",\"signed_volume_mm3\":"<<double(volume)<<",\"native_topology_volume_check_passed\":"<<(passed?"true":"false")<<",\"self_intersections_checked_by_this_program\":false,\"physical_acceptance\":false}\n";
        if(!out)throw std::runtime_error("Report write failed");
        return passed?0:1;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
