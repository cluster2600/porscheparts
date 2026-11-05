#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/Polygon_mesh_processing/shape_predicates.h>
#include <iostream>
#include <vector>

// Read-only independent predicates. Never repair or write the supplied mesh.
int main(int argc, char** argv) {
  using K = CGAL::Exact_predicates_inexact_constructions_kernel;
  using Mesh = CGAL::Surface_mesh<K::Point_3>;
  namespace PMP = CGAL::Polygon_mesh_processing;
  if (argc != 2) return 2;
  Mesh mesh;
  if (!CGAL::IO::read_polygon_mesh(argv[1], mesh) ||
      !CGAL::is_triangle_mesh(mesh)) return 3;
  std::vector<Mesh::Face_index> degenerate;
  PMP::degenerate_faces(mesh, std::back_inserter(degenerate));
  // CGAL intersection predicates must not be fed degenerate triangles.
  if (!degenerate.empty()) {
    std::cout << "{\"degenerate_faces\":" << degenerate.size()
              << ",\"intersection_check_executed\":false}\n";
    return 1;
  }
  std::vector<std::pair<Mesh::Face_index, Mesh::Face_index>> pairs;
  PMP::self_intersections(mesh, std::back_inserter(pairs));
  bool valid = CGAL::is_valid_polygon_mesh(mesh);
  bool closed = CGAL::is_closed(mesh);
  std::cout << "{\"vertices\":" << mesh.number_of_vertices()
            << ",\"faces\":" << mesh.number_of_faces()
            << ",\"degenerate_faces\":0,\"intersection_check_executed\":true"
            << ",\"intersection_pairs\":" << pairs.size()
            << ",\"closed\":" << (closed ? "true" : "false")
            << ",\"valid_polygon_mesh\":" << (valid ? "true" : "false")
            << "}\n";
  return pairs.empty() && valid && closed ? 0 : 1;
}
