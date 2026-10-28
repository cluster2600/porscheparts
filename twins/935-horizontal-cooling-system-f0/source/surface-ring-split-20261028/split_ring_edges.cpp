#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/remesh.h>
#include <CGAL/Polygon_mesh_processing/measure.h>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <vector>

using K = CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;
namespace PMP = CGAL::Polygon_mesh_processing;

int main(int argc,char** argv) {
    if (argc != 3 || std::filesystem::exists(argv[2])) return 2;
    Mesh mesh;
    if (!CGAL::IO::read_polygon_mesh(argv[1],mesh) || !CGAL::is_triangle_mesh(mesh)
        || !CGAL::is_closed(mesh)) return 3;
    const auto before_faces=mesh.number_of_faces();
    const auto before_vertices=mesh.number_of_vertices();
    const double before_volume=CGAL::to_double(PMP::volume(mesh));
    std::vector<Mesh::Edge_index> selected;
    for (auto edge : edges(mesh)) {
        auto h=halfedge(edge,mesh);
        auto a=mesh.point(source(h,mesh));
        auto b=mesh.point(target(h,mesh));
        double r=std::hypot((a.x()+b.x())/2.0,(a.y()+b.y())/2.0);
        if (r>=83.0 && r<87.0) selected.push_back(edge);
    }
    std::cerr << "selected_edges " << selected.size() << '\n';
    PMP::split_long_edges(selected,1.0,mesh);
    if (!CGAL::is_valid_polygon_mesh(mesh) || !CGAL::is_closed(mesh)
        || mesh.number_of_vertices() < before_vertices
        || mesh.number_of_faces() < before_faces
        || !(CGAL::to_double(PMP::volume(mesh))>0)) return 4;
    if (!CGAL::IO::write_polygon_mesh(argv[2],mesh,
        CGAL::parameters::stream_precision(17))) return 5;
    std::cout << "vertices_before " << before_vertices
              << " vertices_after " << mesh.number_of_vertices()
              << " faces_before " << before_faces
              << " faces_after " << mesh.number_of_faces()
              << " volume_before " << before_volume
              << " volume_after " << CGAL::to_double(PMP::volume(mesh)) << '\n';
    return 0;
}
