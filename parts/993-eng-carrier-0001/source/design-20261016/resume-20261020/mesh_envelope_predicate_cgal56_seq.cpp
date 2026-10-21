// CGAL 5.6 derivative: global mesh-to-mesh distance under CGAL's additive-error contract.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/distance.h>
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
constexpr double error_mm = 0.001; // One micron additive API error; fixed acceptance limit unchanged.
constexpr double fixed_limit_mm = 0.06;

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

int main(int argc, char** argv) {
  try {
    static_assert(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits == 53,
                  "IEEE binary64 is required");
    require(argc == 3, "Usage: mesh_envelope_predicate REFERENCE.mesh64 RETAINED.mesh64");
    require(std::string(CGAL_VERSION_STR) == "5.6", "The pinned CGAL release is required");
    const auto reference = read_mesh(argv[1]);
    const auto retained = read_mesh(argv[2]);
    const auto start = std::chrono::steady_clock::now();
    // Keep the 0.06 mm limit, subtract the unchanged additive API error,
    // and round the decision threshold outwards toward the stricter side.
    const auto interval = CGAL::to_interval(K::FT(fixed_limit_mm)-K::FT(error_mm));
    const double guard = std::nextafter(interval.first, -std::numeric_limits<double>::infinity());
    require(K::FT(guard)+K::FT(error_mm) <= K::FT(fixed_limit_mm), "Conservative error guard differs");
    const bool larger = PMP::is_Hausdorff_distance_larger<CGAL::Sequential_tag>(reference, retained, guard, error_mm,
      CGAL::parameters::use_one_sided_hausdorff(false));
    std::cout << std::setprecision(17) << std::boolalpha
      << "{\"schema\":\"CGAL56-complete-symmetric-distance-predicate-1\","
      << "\"CGAL_version\":\"" << CGAL_VERSION_STR << "\","
      << "\"kernel\":\"Epeck\",\"symmetric\":true,"
      << "\"reference_vertices\":" << reference.number_of_vertices()
      << ",\"reference_faces\":" << reference.number_of_faces()
      << ",\"retained_vertices\":" << retained.number_of_vertices()
      << ",\"retained_faces\":" << retained.number_of_faces()
      << ",\"fixed_limit_mm\":" << fixed_limit_mm << ",\"API_additive_error_mm\":" << error_mm
      << ",\"stricter_predicate_threshold_mm\":" << guard
      << ",\"public_predicate_distance_larger\":" << larger
      << ",\"API_contract_envelope_screen_passed\":" << !larger
      << ",\"authority\":\"CGAL public bounded-error symmetric predicate with conservative additive-error guard\","
      << "\"internal_rounding_independently_certified\":false,\"BREP_global_bound\":null,"
      << "\"global_admission\":false,\"measure_wall_seconds\":"
      << std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count() << "}" << std::endl;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << std::endl;
    return 2;
  }
}
