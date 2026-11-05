#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/Polygon_mesh_processing/shape_predicates.h>
#include <iostream>
#include <vector>

// Index-bearing companion; reads only. Face IDs refer to this exact OFF import.
int main(int argc, char** argv) {
  using K = CGAL::Exact_predicates_inexact_constructions_kernel;
  using Mesh = CGAL::Surface_mesh<K::Point_3>;
  namespace PMP = CGAL::Polygon_mesh_processing;
  if (argc != 2) return 2;
  Mesh mesh;
  if (!CGAL::IO::read_polygon_mesh(argv[1], mesh) || !CGAL::is_triangle_mesh(mesh)) return 3;
  std::vector<Mesh::Face_index> degenerate;
  PMP::degenerate_faces(mesh, std::back_inserter(degenerate));
  if (!degenerate.empty()) return 4;
  std::vector<std::pair<Mesh::Face_index, Mesh::Face_index>> pairs;
  PMP::self_intersections(mesh, std::back_inserter(pairs));
  std::cout << "{\"vertices\":" << mesh.number_of_vertices()
            << ",\"triangles\":" << mesh.number_of_faces() << ",\"face_pairs\":[";
  bool first = true;
  for (const auto& pair : pairs) {
    if (!first) std::cout << ",";
    std::cout << "[" << pair.first.idx() << "," << pair.second.idx() << "]";
    first = false;
  }
  std::cout << "]}\n";
  return 0; // Discovery succeeded; pairs are failures of geometry, not of this tool.
}
