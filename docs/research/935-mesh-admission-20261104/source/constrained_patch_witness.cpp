#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/detect_features.h>
#include <CGAL/Polygon_mesh_processing/remesh.h>
#include <CGAL/Polygon_mesh_processing/Uniform_sizing_field.h>
#include <CGAL/Polygon_mesh_processing/shape_predicates.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <vector>

// Uniform-field software witness and real-input preflight, not head admission.
int main(int argc, char** argv) {
  using K = CGAL::Exact_predicates_inexact_constructions_kernel;
  using Mesh = CGAL::Surface_mesh<K::Point_3>;
  namespace PMP = CGAL::Polygon_mesh_processing;
  try {
    if (argc != 6 && argc != 7) return 2;
    bool preflight_only = argc == 7 && std::string(argv[6]) == "--preflight-only";
    if (argc == 7 && !preflight_only) return 2;
    const double target_length = std::stod(argv[3]);
    if (!std::isfinite(target_length) || target_length <= 0) return 2;
    if (std::ifstream(argv[4]).good() || std::ifstream(argv[5]).good()) return 3;
    Mesh mesh;
    if (!CGAL::IO::read_polygon_mesh(argv[1], mesh) || !CGAL::is_triangle_mesh(mesh)) return 4;
    std::vector<Mesh::Face_index> degenerate;
    PMP::degenerate_faces(mesh, std::back_inserter(degenerate));
    if (!degenerate.empty()) return 4;
    std::ifstream mask(argv[2]);
    if (!mask) return 4;
    std::set<std::size_t> protected_ids;
    std::size_t id;
    while (mask >> id) {
      if (id >= mesh.number_of_faces() || !protected_ids.insert(id).second) return 4;
    }
    if (!mask.eof() || protected_ids.empty()) return 4;
    auto constrained_edges = mesh.add_property_map<Mesh::Edge_index, bool>("e:locked", false).first;
    auto constrained_vertices = mesh.add_property_map<Mesh::Vertex_index, bool>("v:locked", false).first;
    PMP::detect_sharp_edges(mesh, 30., constrained_edges);
    std::vector<Mesh::Face_index> selected;
    for (auto face : mesh.faces()) {
      if (protected_ids.count(face.idx())) {
        for (auto h : CGAL::halfedges_around_face(mesh.halfedge(face), mesh))
          constrained_edges[mesh.edge(h)] = true;
      } else selected.push_back(face);
    }
    for (auto e : mesh.edges()) {
      if (CGAL::is_border(e, mesh)) constrained_edges[e] = true;
      if (constrained_edges[e]) {
        auto h = mesh.halfedge(e);
        constrained_vertices[mesh.source(h)] = true;
        constrained_vertices[mesh.target(h)] = true;
      }
    }
    PMP::Uniform_sizing_field<Mesh> sizing(target_length, mesh);
    std::size_t locked = 0, too_long = 0, locked_vertices = 0;
    double maximum = 0;
    for (auto e : mesh.edges()) if (constrained_edges[e]) {
      ++locked; auto h = mesh.halfedge(e);
      maximum = std::max(maximum, std::sqrt(CGAL::to_double(CGAL::squared_distance(mesh.point(mesh.source(h)), mesh.point(mesh.target(h))))));
      if (sizing.is_too_long(mesh.source(h), mesh.target(h), mesh)) ++too_long;
    }
    for (auto v : mesh.vertices()) if (constrained_vertices[v]) ++locked_vertices;
    std::ofstream report(argv[5]);
    report << std::setprecision(17) << "{\"vertices\":" << mesh.number_of_vertices()
           << ",\"triangles\":" << mesh.number_of_faces()
           << ",\"protected_faces\":" << protected_ids.size()
           << ",\"locked_edges\":" << locked << ",\"locked_vertices\":" << locked_vertices
           << ",\"target_mm\":" << target_length << ",\"max_locked_edge_mm\":" << maximum
           << ",\"oversize_locked_edges\":" << too_long
           << ",\"installed_long_edge_factor\":" << 4./3.
           << ",\"preflight_only\":" << (preflight_only ? "true" : "false")
           << ",\"length_precondition_passed\":" << (too_long == 0 ? "true" : "false")
           << ",\"remeshing_requested_after_preflight\":" << (!preflight_only && too_long == 0 ? "true" : "false") << "}\n";
    report.close();
    if (too_long) return 5;
    if (preflight_only) return 0;
    PMP::isotropic_remeshing(selected, sizing, mesh,
        CGAL::parameters::edge_is_constrained_map(constrained_edges)
          .vertex_is_constrained_map(constrained_vertices).protect_constraints(true)
          .relax_constraints(false).number_of_iterations(3)
          .number_of_relaxation_steps(1).do_project(true));
    if (!CGAL::IO::write_polygon_mesh(argv[4], mesh, CGAL::parameters::stream_precision(17))) return 6;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n'; return 7;
  }
}
