#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polygon_mesh_processing/corefinement.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/boost/graph/helpers.h>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>

using Kernel=CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh=CGAL::Surface_mesh<Kernel::Point_3>;
namespace PMP=CGAL::Polygon_mesh_processing;

int main(int argc,char** argv) {
  try {
    if(argc!=5 && argc!=6) throw std::runtime_error("Usage: exact_union A.off B.off NEW_OUTPUT.off NEW_REPORT.json [B_INVERSE_FRAME.txt]");
    if(std::ifstream(argv[3]).good() || std::ifstream(argv[4]).good()) throw std::runtime_error("Refusing existing output");
    const auto start=std::chrono::steady_clock::now();
    Mesh a,b,out;
    for(auto pair : {std::make_pair(argv[1],&a),std::make_pair(argv[2],&b)}) {
      if(!CGAL::IO::read_polygon_mesh(pair.first,*pair.second) || !CGAL::is_triangle_mesh(*pair.second) || !CGAL::is_closed(*pair.second))
        throw std::runtime_error("Input must be a closed triangle mesh");
      std::cerr<<pair.first<<": "<<pair.second->number_of_vertices()<<" vertices, "<<pair.second->number_of_faces()<<" faces\n";
    }
    if(argc==6) {
      std::ifstream frame(argv[5]); Kernel::FT matrix[9],offset[3];
      for(auto& x:matrix) if(!(frame>>x)) throw std::runtime_error("Invalid frame matrix");
      for(auto& x:offset) if(!(frame>>x)) throw std::runtime_error("Invalid frame offset");
      for(auto v:b.vertices()) {
        auto p=b.point(v); Kernel::FT q[3]={p.x()-offset[0],p.y()-offset[1],p.z()-offset[2]};
        b.point(v)=Kernel::Point_3(matrix[0]*q[0]+matrix[1]*q[1]+matrix[2]*q[2],matrix[3]*q[0]+matrix[4]*q[1]+matrix[5]*q[2],matrix[6]*q[0]+matrix[7]*q[1]+matrix[8]*q[2]);
      }
      std::cerr<<"Applied B inverse frame using exact arithmetic\n";
    }
    if(!PMP::corefine_and_compute_union(a,b,out,CGAL::parameters::throw_on_self_intersection(true)))
      throw std::runtime_error("Exact union did not produce a manifold output");
    if(!CGAL::is_valid_polygon_mesh(out) || !CGAL::is_triangle_mesh(out) || !CGAL::is_closed(out))
      throw std::runtime_error("Exact Boolean topology check failed");
    out.collect_garbage();
    if(!CGAL::IO::write_polygon_mesh(argv[3],out,CGAL::parameters::stream_precision(17)))
      throw std::runtime_error("Output write failed");
    const auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::ofstream report(argv[4]);
    report<<"{\n  \"kernel\": \"CGAL EPECK\",\n  \"vertices\": "<<out.number_of_vertices()
          <<",\n  \"triangles\": "<<out.number_of_faces()<<",\n  \"closed_valid_triangle_mesh\": true,\n  \"seconds\": "<<seconds
          <<",\n  \"independent_export_validation_required\": true,\n  \"manufacturing_qualified\": false\n}\n";
    std::cerr<<"Exact union exported in "<<seconds<<" seconds\n";
  } catch(const std::exception& error) {
    std::cerr<<"FAILED: "<<error.what()<<'\n';return 2;
  }
}
