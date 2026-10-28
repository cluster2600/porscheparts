#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <iostream>
#include <vector>

using K = CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    Mesh mesh;
    if (!CGAL::IO::read_polygon_mesh(argv[1], mesh) || mesh.number_of_faces() == 0
        || mesh.number_of_faces() > 4000000 || !CGAL::is_triangle_mesh(mesh)
        || !CGAL::is_valid_polygon_mesh(mesh) || !CGAL::is_closed(mesh)) return 3;
    for (auto v : mesh.vertices())
        for (int i = 0; i < 3; ++i)
            if (!std::isfinite(CGAL::to_double(mesh.point(v)[i]))) return 3;
    std::vector<std::pair<Mesh::Face_index, Mesh::Face_index>> intersections;
    CGAL::Polygon_mesh_processing::self_intersections(mesh, std::back_inserter(intersections));
    std::cout << "{\"vertices\":" << mesh.number_of_vertices()
              << ",\"faces\":" << mesh.number_of_faces()
              << ",\"closed_valid_triangle_mesh\":true,\"self_intersection_pairs\":"
              << intersections.size() << ",\"first_pairs\":[";
    for (std::size_t i = 0; i < std::min(std::size_t(10), intersections.size()); ++i) {
        if (i) std::cout << ',';
        std::cout << '[' << intersections[i].first.idx() << ',' << intersections[i].second.idx() << ']';
    }
    std::cout << "]}\n";
    return intersections.empty() ? 0 : 4;
}
