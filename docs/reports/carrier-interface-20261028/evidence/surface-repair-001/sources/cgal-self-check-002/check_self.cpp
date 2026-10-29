// Independent exact-predicate self-intersection checks on complete binary64 triangle meshes.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/number_utils.h>
#include <CGAL/version.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
#include <vector>

using K = CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;
namespace PMP = CGAL::Polygon_mesh_processing;

void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}

std::size_t index_token(std::istream& input) {
  std::string token;
  input >> token;
  require(bool(input) && !token.empty() && token.find_first_not_of("0123456789") == std::string::npos,
          "A nonnegative decimal integer is required");
  const unsigned long long n = std::stoull(token);
  require(n <= std::numeric_limits<std::size_t>::max(), "Index overflow");
  return static_cast<std::size_t>(n);
}

Mesh read_mesh(const char* filename) {
  // Existing native mesh64 transport: decimal17 IEEE coordinates, then integer rows.
  // A future encoder must prove binary64 roundtrip against the actual NPZ/STL arrays.
  std::ifstream input(filename);
  input.imbue(std::locale::classic());
  require(bool(input), "Cannot open the frozen mesh transport");
  const auto nv = index_token(input), nf = index_token(input);
  require(nv > 0 && nf > 0, "A nonempty mesh is required");
  Mesh mesh;
  std::vector<Mesh::Vertex_index> vertices;
  std::vector<bool> used(nv, false);
  vertices.reserve(nv);
  for (std::size_t i = 0; i < nv; ++i) {
    double x, y, z;
    input >> x >> y >> z;
    require(bool(input) && std::isfinite(x) && std::isfinite(y) && std::isfinite(z),
            "Finite binary64 coordinates are required");
    // Parse to double first. FT(double) preserves its exact dyadic value.
    vertices.push_back(mesh.add_vertex(K::Point_3(K::FT(x), K::FT(y), K::FT(z))));
  }
  for (std::size_t i = 0; i < nf; ++i) {
    const std::array<std::size_t, 3> row{{index_token(input), index_token(input), index_token(input)}};
    require(row[0] < nv && row[1] < nv && row[2] < nv &&
            row[0] != row[1] && row[1] != row[2] && row[0] != row[2], "Invalid triangle indices");
    const auto a = vertices[row[0]], b = vertices[row[1]], c = vertices[row[2]];
    require(!CGAL::collinear(mesh.point(a), mesh.point(b), mesh.point(c)),
            "An exactly zero-area triangle is forbidden");
    require(mesh.add_face(a, b, c) != Mesh::null_face(),
            "Face insertion failed; no automatic orientation or topology repair is permitted");
    for (const auto v : row) used[v] = true;
  }
  input >> std::ws;
  require(input.eof(), "Unexpected trailing mesh data");
  for (const bool present : used) require(present, "Unused input vertex");
  require(mesh.number_of_vertices() == nv && mesh.number_of_faces() == nf &&
          CGAL::is_triangle_mesh(mesh) && CGAL::is_closed(mesh) && CGAL::is_valid_polygon_mesh(mesh),
          "One complete closed oriented triangular transport is required");
  return mesh;
}


void append_tetra(Mesh& mesh, K::FT x, K::FT y, K::FT z) {
  auto a=mesh.add_vertex(K::Point_3(x,y,z));
  auto b=mesh.add_vertex(K::Point_3(x+1,y,z));
  auto c=mesh.add_vertex(K::Point_3(x,y+1,z));
  auto d=mesh.add_vertex(K::Point_3(x,y,z+1));
  mesh.add_face(a,c,b);mesh.add_face(a,b,d);mesh.add_face(a,d,c);mesh.add_face(b,c,d);
}
int main(int argc,char** argv) {
  try {
    require(argc==4,"FIRST.mesh64 SECOND.mesh64 OUTPUT.json");
    Mesh tetra,overlap,separate;append_tetra(tetra,0,0,0);
    append_tetra(overlap,0,0,0);append_tetra(overlap,K::FT(1)/4,K::FT(1)/4,K::FT(1)/4);
    append_tetra(separate,0,0,0);append_tetra(separate,3,0,0);
    require(!PMP::does_self_intersect<CGAL::Sequential_tag>(tetra),"Tetrahedron control failed");
    require(PMP::does_self_intersect<CGAL::Sequential_tag>(overlap),"Intersecting closed components were missed");
    require(!PMP::does_self_intersect<CGAL::Sequential_tag>(separate),"Separate components control failed");
    auto first=read_mesh(argv[1]);auto second=read_mesh(argv[2]);
    auto start=std::chrono::steady_clock::now();
    bool a=PMP::does_self_intersect<CGAL::Sequential_tag>(first);
    bool b=PMP::does_self_intersect<CGAL::Sequential_tag>(second);

    if(b){
      std::vector<std::pair<Mesh::Face_index,Mesh::Face_index>> pairs;
      PMP::self_intersections<CGAL::Sequential_tag>(second,std::back_inserter(pairs));
      std::ofstream witnesses(std::string(argv[3])+".witnesses.json");
      witnesses<<std::setprecision(17)<<"{\"intersecting_face_pair_count\":"<<pairs.size()<<",\"examples\":[";
      for(std::size_t i=0;i<std::min<std::size_t>(pairs.size(),12);++i){
        if(i)witnesses<<",";witnesses<<"{\"faces\":["<<pairs[i].first.idx()<<","<<pairs[i].second.idx()<<"],\"triangles\":[";
        int face_count=0;for(auto face:{pairs[i].first,pairs[i].second}){
          if(face_count++)witnesses<<",";witnesses<<"[";int vertex_count=0;
          for(auto vertex:CGAL::vertices_around_face(second.halfedge(face),second)){
            if(vertex_count++)witnesses<<",";const auto& p=second.point(vertex);
            witnesses<<"["<<CGAL::to_double(p.x())<<","<<CGAL::to_double(p.y())<<","<<CGAL::to_double(p.z())<<"]";
          }witnesses<<"]";
        }witnesses<<"]}";
      }witnesses<<"]}\n";
    }
    std::ofstream out(argv[3]);out<<std::setprecision(17)<<std::boolalpha
      <<"{\"status\":\""<<(!a&&!b?"complete_self_intersection_screen_passed":"self_intersection_screen_refused")<<"\","
      <<"\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPECK\",\"controls_passed\":true,"
      <<"\"coordinate_semantics\":\"exact dyadic FT(double), complete input roster\","
      <<"\"first_vertices\":"<<first.number_of_vertices()<<",\"first_triangles\":"<<first.number_of_faces()
      <<",\"second_vertices\":"<<second.number_of_vertices()<<",\"second_triangles\":"<<second.number_of_faces()
      <<",\"first_self_intersects\":"<<a<<",\"second_self_intersects\":"<<b
      <<",\"elapsed_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
      <<",\"manufacturing_authorized\":false}\n";
    require(bool(out),"Output write failed");return a||b?2:0;
  } catch(const std::exception& error){std::cerr<<error.what()<<std::endl;return 70;}
}
