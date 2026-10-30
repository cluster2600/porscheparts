#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_slicer.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/boost/graph/helpers.h>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<K::Point_3>;
int main(int argc,char** argv) {
  try {
    if(argc!=5) throw std::runtime_error("Usage: slice_exact ALIGNED.off LAYER_MM NEW.cli NEW.json");
    if(std::ifstream(argv[3]).good() || std::ifstream(argv[4]).good()) throw std::runtime_error("Refusing existing output");
    auto start=std::chrono::steady_clock::now();Mesh mesh;
    if(!CGAL::IO::read_polygon_mesh(argv[1],mesh) || !CGAL::is_closed(mesh) || !CGAL::is_triangle_mesh(mesh)) throw std::runtime_error("Invalid mesh");
    double dz=std::stod(argv[2]),zmax=0,zmin=1e9;
    if(!(dz>0 && dz<=1)) throw std::runtime_error("Invalid layer height");
    for(auto v:mesh.vertices()){double z=CGAL::to_double(mesh.point(v).z());zmax=std::max(zmax,z);zmin=std::min(zmin,z);}
    if(zmin < -1e-9) throw std::runtime_error("Geometry extends below the slicing origin");
    int layers=static_cast<int>(std::ceil(zmax/dz));
    CGAL::Polygon_mesh_slicer<Mesh,K> slicer(mesh);
    std::ofstream out(argv[3]);out<<std::fixed<<std::setprecision(12);
    out<<"$$HEADERSTART\n$$ASCII\n$$UNITS/1.0\n$$VERSION/200\n$$LABEL/1,\"935 conditional study - no machine qualification\"\n$$LAYERS/"<<layers+1<<"\n$$HEADEREND\n$$GEOMETRYSTART\n$$LAYER/0.0\n";
    std::size_t contours=0,vertices=0;long double integrated=0;
    for(int layer=1;layer<=layers;++layer) {
      K::FT height=K::FT(layer)*K::FT(dz);std::vector<std::vector<K::Point_3>> loops;
      slicer(K::Plane_3(0,0,1,-height),std::back_inserter(loops));
      out<<"$$LAYER/"<<CGAL::to_double(height)<<'\n';K::FT layer_area=0;
      for(const auto& loop:loops) {
        if(loop.size()<4 || loop.front()!=loop.back()) throw std::runtime_error("Non-closed or degenerate contour");
        K::FT area=0;auto origin=loop.front();
        for(std::size_t i=1;i<loop.size();++i) area+=(loop[i-1].x()-origin.x())*(loop[i].y()-origin.y())-(loop[i].x()-origin.x())*(loop[i-1].y()-origin.y());
        if(area==0) throw std::runtime_error("Zero-area contour");
        layer_area+=area/2;out<<"$$POLYLINE/1,"<<(area>0?1:0)<<','<<loop.size();
        for(const auto& p:loop)out<<','<<CGAL::to_double(p.x())<<','<<CGAL::to_double(p.y());
        out<<'\n';contours++;vertices+=loop.size();
      }
      integrated+=CGAL::to_double(layer_area)*dz;
      if(layer%100==0){out.flush();std::cerr<<"Layer "<<layer<<'/'<<layers<<" contours "<<contours<<'\n';}
    }
    out<<"$$GEOMETRYEND\n";out.close();if(!out)throw std::runtime_error("CLI write failed");
    double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::ofstream report(argv[4]);report<<std::setprecision(17)<<"{\n  \"kernel\": \"CGAL EPECK\",\n  \"layers\": "<<layers<<",\n  \"layer_mm\": "<<dz<<",\n  \"contours\": "<<contours<<",\n  \"vertices\": "<<vertices<<",\n  \"right_endpoint_slice_volume_mm3\": "<<static_cast<double>(integrated)<<",\n  \"seconds\": "<<seconds<<",\n  \"independent_contour_validation_required\": true,\n  \"machine_job\": false,\n  \"manufacturing_qualified\": false\n}\n";
  } catch(const std::exception& e){std::cerr<<"FAILED: "<<e.what()<<'\n';return 2;}
}
