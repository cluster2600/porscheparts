// Local adapter for the external CGAL kernel; dependencies retain their licences.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/autorefinement.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

using K=CGAL::Exact_predicates_exact_constructions_kernel;
using Point=K::Point_3;
using Triangle=std::array<std::size_t,3>;
namespace PMP=CGAL::Polygon_mesh_processing;
struct SourceVisitor : PMP::Autorefinement::Default_visitor {
  std::vector<std::size_t>* sources;
  explicit SourceVisitor(std::vector<std::size_t>& s):sources(&s){}
  void number_of_output_triangles(std::size_t n) {
    sources->assign(n,std::numeric_limits<std::size_t>::max());
  }
  void verbatim_triangle_copy(std::size_t target,std::size_t source) { sources->at(target)=source; }
  void new_subtriangle(std::size_t target,std::size_t source) { sources->at(target)=source; }
};

int main(int argc,char** argv) {
  if(argc!=6) {
    std::cerr<<"Usage: autorefine INPUT.mesh64 OUTPUT.mesh64 RECEIPT.json GRID_BITS ITERATIONS\n";
    return 64;
  }
  try {
    const int bits=std::stoi(argv[4]),iterations=std::stoi(argv[5]);
    if(bits<0 || bits>=52 || iterations<0 || iterations>100)
      throw std::runtime_error("Invalid explicit grid bits or iteration budget");
    std::ifstream input(argv[1]);
    std::size_t nv=0,nf=0;input>>nv>>nf;
    if(!input || nv==0 || nf==0)throw std::runtime_error("Empty or invalid mesh64 input");
    std::vector<Point> points;points.reserve(nv);
    std::array<double,3> lo{INFINITY,INFINITY,INFINITY},hi{-INFINITY,-INFINITY,-INFINITY};
    for(std::size_t i=0;i<nv;++i) {
      double x,y,z;input>>x>>y>>z;
      if(!input || !std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z))
        throw std::runtime_error("Nonfinite or truncated input vertex");
      // Construct from doubles, so exact values are the original IEEE floats,
      // not the different rational numbers denoted by their decimal strings.
      points.emplace_back(x,y,z);
      const std::array<double,3> xyz{x,y,z};
      for(int j=0;j<3;++j){lo[j]=(std::min)(lo[j],xyz[j]);hi[j]=(std::max)(hi[j],xyz[j]);}
    }
    std::vector<Triangle> triangles(nf);
    for(auto& t:triangles) {
      input>>t[0]>>t[1]>>t[2];
      if(!input || t[0]>=nv || t[1]>=nv || t[2]>=nv)
        throw std::runtime_error("Invalid face index");
    }
    const auto start=std::chrono::steady_clock::now();
    const auto algorithm_bbox=CGAL::bbox_3(points.begin(),points.end());
    lo={algorithm_bbox.xmin(),algorithm_bbox.ymin(),algorithm_bbox.zmin()};
    hi={algorithm_bbox.xmax(),algorithm_bbox.ymax(),algorithm_bbox.zmax()};
    std::vector<std::size_t> sources;SourceVisitor visitor(sources);
    const bool success=PMP::autorefine_triangle_soup(points,triangles,
      CGAL::parameters::apply_iterative_snap_rounding(true)
        .snap_grid_size(bits)
        .number_of_iterations(static_cast<unsigned>(iterations))
        .concurrency_tag(CGAL::Sequential_tag()).visitor(visitor));
    const bool lineage_complete=success && sources.size()==triangles.size() &&
      std::all_of(sources.begin(),sources.end(),[nf](std::size_t i){return i<nf;});
    bool double_exact=true;
    std::vector<Point> rounded;rounded.reserve(points.size());
    for(const auto& p:points) {
      const double x=CGAL::to_double(p.x()),y=CGAL::to_double(p.y()),z=CGAL::to_double(p.z());
      if(!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z))
        throw std::runtime_error("Nonfinite output coordinate");
      rounded.emplace_back(x,y,z);
      double_exact=double_exact && rounded.back()==p;
    }
    std::size_t degenerate=0;
    for(const auto& t:triangles) {
      if(t[0]>=rounded.size() || t[1]>=rounded.size() || t[2]>=rounded.size())
        throw std::runtime_error("Invalid output face index");
      if(CGAL::collinear(rounded[t[0]],rounded[t[1]],rounded[t[2]]))++degenerate;
    }
    // This test is on the actual exported IEEE values, after conversion.
    // Return false/partial is retained without pretending it was repaired.
    const bool post_double_clean=success && !PMP::does_triangle_soup_self_intersect(rounded,triangles);
    std::ofstream output(argv[2]);output<<rounded.size()<<' '<<triangles.size()<<'\n'<<std::setprecision(17);
    for(const auto& p:rounded)output<<CGAL::to_double(p.x())<<' '<<CGAL::to_double(p.y())<<' '<<CGAL::to_double(p.z())<<'\n';
    for(const auto& t:triangles)output<<t[0]<<' '<<t[1]<<' '<<t[2]<<'\n';
    if(!output)throw std::runtime_error("Could not write output mesh");
    if(lineage_complete) {
      std::ofstream lineage(std::string(argv[2])+".source_faces");
      for(auto i:sources)lineage<<i<<'\n';
      if(!lineage)throw std::runtime_error("Could not write source-face lineage");
    }
    std::array<double,3> max_abs,scale,step;std::array<int,3> exponents;
    double step_norm2=0;
    for(int j=0;j<3;++j){
      max_abs[j]=(std::max)(-lo[j],hi[j]);std::frexp(max_abs[j],&exponents[j]);
      scale[j]=std::ldexp(1.,bits-exponents[j]-1);step[j]=1./scale[j];step_norm2+=step[j]*step[j];
    }
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::ofstream receipt(argv[3]);
    receipt<<std::boolalpha<<std::setprecision(17)
      <<"{\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"CGAL_commit\":\""<<CGAL_STR(CGAL_GIT_HASH)
      <<"\",\"native_return\":"<<success<<",\"all_output_coordinates_exactly_double\":"<<double_exact
      <<",\"post_double_self_intersection_free\":"<<post_double_clean
      <<",\"exact_collinear_output_triangles\":"<<degenerate
      <<",\"source_face_lineage_complete\":"<<lineage_complete
      <<",\"input_vertices\":"<<nv<<",\"input_faces\":"<<nf
      <<",\"output_vertices\":"<<rounded.size()<<",\"output_faces\":"<<triangles.size()
      <<",\"snap_grid_bits\":"<<bits<<",\"iteration_budget\":"<<iterations
      <<",\"seconds\":"<<seconds<<",\"kernel\":\"Epeck; original input IEEE doubles\""
      <<",\"bbox_mm\":[["<<lo[0]<<','<<lo[1]<<','<<lo[2]<<"],["<<hi[0]<<','<<hi[1]<<','<<hi[2]<<"]]"
      <<",\"maximum_absolute_coordinates_mm\":["<<max_abs[0]<<','<<max_abs[1]<<','<<max_abs[2]<<']'
      <<",\"frexp_exponents\":["<<exponents[0]<<','<<exponents[1]<<','<<exponents[2]<<']'
      <<",\"grid_scale_per_mm\":["<<scale[0]<<','<<scale[1]<<','<<scale[2]<<']'
      <<",\"grid_step_mm\":["<<step[0]<<','<<step[1]<<','<<step[2]<<']'
      <<",\"maximum_rounding_displacement_per_iteration_mm\":"<<std::sqrt(step_norm2)/2
      <<",\"cumulative_rounding_budget_mm\":"<<iterations*std::sqrt(step_norm2)/2<<"}\n";
    return success && double_exact && post_double_clean && degenerate==0 && lineage_complete ? 0 : 2;
  } catch(const std::exception& error) {
    std::cerr<<error.what()<<'\n';return 70;
  }
}
