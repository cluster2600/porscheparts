// Independent exact-predicate self-intersection checks on complete binary64 triangle meshes.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_face_graph_triangle_primitive.h>
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

using Primitive=CGAL::AABB_face_graph_triangle_primitive<Mesh>;
using Traits=CGAL::AABB_traits<K,Primitive>;
using Tree=CGAL::AABB_tree<Traits>;
int main(int argc,char**argv){try{
 require(argc==5,"SOURCE TARGET VERTEX_INDEX OUTPUT");Mesh control;append_tetra(control,0,0,0);Tree ct(faces(control).first,faces(control).second,control);ct.accelerate_distance_queries();require(ct.squared_distance(K::Point_3(0,0,2))==K::FT(1)&&ct.squared_distance(K::Point_3(0,0,0))==K::FT(0),"Exact closest-distance controls failed");
 Mesh source=read_mesh(argv[1]),target=read_mesh(argv[2]);std::size_t index=std::stoull(argv[3]);require(index<source.number_of_vertices(),"Source vertex outside roster");Tree tree(faces(target).first,faces(target).second,target);tree.accelerate_distance_queries();auto p=source.point(Mesh::Vertex_index(index));auto distance=tree.squared_distance(p);bool refused=distance>K::FT(1)/10000;
 std::ofstream out(argv[4]);out<<std::setprecision(17)<<std::boolalpha<<"{\"status\":\""<<(refused?"exact_vertex_witness_disproves_0_01mm_fidelity":"no_refusal_from_this_vertex")<<"\",\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPECK\",\"controls_passed\":true,\"source_vertex\":"<<index<<",\"source_point_mm\":["<<CGAL::to_double(p.x())<<","<<CGAL::to_double(p.y())<<","<<CGAL::to_double(p.z())<<"],\"exact_squared_distance_mm2\":\""<<CGAL::exact(distance)<<"\",\"displayed_distance_mm\":"<<std::sqrt(CGAL::to_double(distance))<<",\"disproves_0_01mm_fidelity\":"<<refused<<",\"manufacturing_authorized\":false}\n";require(bool(out),"Output write failed");return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 70;}}
