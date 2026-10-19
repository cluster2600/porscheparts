// Conservative exact set-union reduction of affine-roof vertical prisms.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_2.h>
#include <CGAL/Polygon_set_2.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <list>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
using K=CGAL::Exact_predicates_exact_constructions_kernel;
using FT=K::FT;using Point=K::Point_3;using Polygon=CGAL::Polygon_2<K>;
using Set=CGAL::Polygon_set_2<K>;using Face=std::array<std::size_t,3>;
std::string rational(const FT& value){std::ostringstream out;out<<CGAL::exact(value);return out.str();}
struct Patch {FT height;std::vector<std::size_t> faces;std::vector<Polygon> polygons;std::unique_ptr<Set> region;};
struct Certificate {std::size_t face,patch;FT maximum,area;bool horizontal;};
int main(int argc,char** argv) {
  if(argc!=4){std::cerr<<"Usage: dominance INPUT.mesh64 RECEIPT.json FLOOR_Z_MM\n";return 64;}
  try {
    const auto start=std::chrono::steady_clock::now();const double floor_double=std::stod(argv[3]);
    if(floor_double!=0 || !std::isfinite(floor_double))throw std::runtime_error("This proof requires explicit common floor z=0");
    const FT floor(floor_double);std::ifstream input(argv[1]);std::size_t nv=0,nf=0;input>>nv>>nf;
    if(!input || nv==0 || nf==0)throw std::runtime_error("Empty input");
    std::vector<Point> vertices;vertices.reserve(nv);
    for(std::size_t i=0;i<nv;++i) {
      double x,y,z;input>>x>>y>>z;
      if(!input || !std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z)||z<floor_double)throw std::runtime_error("Invalid coordinate or roof below common floor");
      vertices.emplace_back(x,y,z);
    }
    std::vector<Face> faces(nf);std::vector<Polygon> polygons(nf);std::vector<FT> maximum(nf);std::vector<bool> horizontal(nf),degenerate(nf);
    std::map<FT,Patch> groups;
    for(std::size_t i=0;i<nf;++i) {
      auto& f=faces[i];input>>f[0]>>f[1]>>f[2];if(!input || f[0]>=nv||f[1]>=nv||f[2]>=nv)throw std::runtime_error("Invalid face");
      const auto& a=vertices[f[0]];const auto& b=vertices[f[1]];const auto& c=vertices[f[2]];
      maximum[i]=(std::max)(a.z(),(std::max)(b.z(),c.z()));horizontal[i]=a.z()==b.z() && b.z()==c.z();
      polygons[i].push_back(K::Point_2(a.x(),a.y()));polygons[i].push_back(K::Point_2(b.x(),b.y()));polygons[i].push_back(K::Point_2(c.x(),c.y()));
      degenerate[i]=polygons[i].area()==0;
      if(degenerate[i])continue; // No positive-area argument is used for an edge.
      if(polygons[i].orientation()==CGAL::CLOCKWISE)polygons[i].reverse_orientation();
      if(horizontal[i]) {
        auto it=groups.find(a.z());if(it==groups.end())it=groups.emplace(a.z(),Patch{a.z(),{},{},nullptr}).first;
        it->second.faces.push_back(i);it->second.polygons.push_back(polygons[i]);
      }
    }
    std::vector<Patch*> patches;
    for(auto& item:groups) {
      auto& patch=item.second;patch.region=std::make_unique<Set>();
      patch.region->join(patch.polygons.begin(),patch.polygons.end());patches.push_back(&patch);
    }
    std::vector<Certificate> removed;std::vector<std::size_t> kept,kept_degenerate;
    std::size_t coverage_tests=0;
    for(std::size_t i=0;i<nf;++i) {
      bool covered=false;
      if(degenerate[i])kept_degenerate.push_back(i);
      else for(std::size_t j=0;j<patches.size();++j) {
        const auto& patch=*patches[j];
        if(patch.height<maximum[i] || (horizontal[i] && patch.height<=maximum[i]))continue;
        ++coverage_tests;Set difference(polygons[i]);difference.difference(*patch.region);
        if(difference.is_empty()) {
          removed.push_back(Certificate{i,j,maximum[i],polygons[i].area(),horizontal[i]});covered=true;break;
        }
      }
      if(!covered)kept.push_back(i);
    }
    std::ofstream out(argv[2]);out<<std::setprecision(17)<<std::boolalpha
      <<"{\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"CGAL_commit\":\""<<CGAL_STR(CGAL_GIT_HASH)
      <<"\",\"kernel\":\"Epeck original IEEE doubles; Polygon_set_2 exact regularized difference\",\"floor_z_mm\":0"
      <<",\"input_vertices\":"<<nv<<",\"input_faces\":"<<nf<<",\"retained_faces\":"<<kept.size()<<",\"removed_faces\":"<<removed.size()
      <<",\"coverage_tests\":"<<coverage_tests<<",\"horizontal_patches\":[";
    for(std::size_t j=0;j<patches.size();++j) {
      if(j)out<<',';const auto& p=*patches[j];out<<"{\"patch_index\":"<<j<<",\"height_mm\":"<<CGAL::to_double(p.height)<<",\"height_exact\":\""<<rational(p.height)<<"\",\"input_face_indices\":[";
      for(std::size_t k=0;k<p.faces.size();++k){if(k)out<<',';out<<p.faces[k];}out<<"]}";
    }
    out<<"],\"certificates\":[";
    for(std::size_t k=0;k<removed.size();++k) {
      if(k)out<<',';const auto& c=removed[k];out<<"{\"input_face_index\":"<<c.face<<",\"covering_patch_index\":"<<c.patch
        <<",\"maximum_roof_z_exact\":\""<<rational(c.maximum)<<"\",\"projected_area_exact\":\""<<rational(c.area)
        <<"\",\"candidate_horizontal\":"<<c.horizontal<<",\"whole_triangle_difference_empty\":true,\"height_bound_exact\":true}";
    }
    out<<"],\"retained_input_face_indices\":[";for(std::size_t k=0;k<kept.size();++k){if(k)out<<',';out<<kept[k];}
    out<<"],\"retained_degenerate_projection_face_indices\":[";for(std::size_t k=0;k<kept_degenerate.size();++k){if(k)out<<',';out<<kept_degenerate[k];}
    out<<"],\"pass\":true,\"scope\":\"Preserves geometric SET UNION of closed positive vertical prisms with common floor zero and affine roofs; not sums, signed chains or multiplicity. Horizontal dependencies strictly increase in height. No coordinate changes.\",\"seconds\":"
      <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
    if(!out)throw std::runtime_error("Could not write proof");return 0;
  }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 70;}
}
