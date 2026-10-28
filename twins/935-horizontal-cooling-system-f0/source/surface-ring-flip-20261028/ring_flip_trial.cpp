#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/remesh.h>
#include <CGAL/Polygon_mesh_processing/measure.h>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <vector>

using K = CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;
namespace PMP = CGAL::Polygon_mesh_processing;

int main(int argc, char** argv) {
    if (argc != 3 || std::filesystem::exists(argv[2])) return 2;
    Mesh mesh;
    if (!CGAL::IO::read_polygon_mesh(argv[1], mesh) || !CGAL::is_triangle_mesh(mesh)
        || !CGAL::is_closed(mesh)) return 3;
    const auto faces_before = mesh.number_of_faces();
    const auto vertices_before = mesh.number_of_vertices();
    const auto volume_before = CGAL::to_double(PMP::volume(mesh));
    auto constrained = mesh.add_property_map<Mesh::Edge_index, bool>("e:constrained", false).first;
    std::size_t constrained_count = 0;
    for (auto edge : edges(mesh)) {
        auto h = halfedge(edge,mesh);
        auto ho = opposite(h,mesh);
        bool fixed = is_border(h,mesh) || is_border(ho,mesh);
        if (!fixed) {
            auto a = mesh.point(source(h,mesh));
            auto b = mesh.point(target(h,mesh));
            auto c = mesh.point(target(next(h,mesh),mesh));
            auto d = mesh.point(target(next(ho,mesh),mesh));
            auto n1 = CGAL::cross_product(b-a,c-a);
            auto n2 = CGAL::cross_product(b-a,d-a);
            double l1 = std::sqrt(n1.squared_length());
            double l2 = std::sqrt(n2.squared_length());
            if (!(l1 > 0 && l2 > 0)) {
                fixed = true;
            } else {
                double delta = std::max(std::abs((d-a)*n1)/l1,
                                        std::abs((c-a)*n2)/l2);
                fixed = !(std::isfinite(delta) && delta <= .001);
            }
        }
        put(constrained,edge,fixed);
        constrained_count += fixed;
    }
    std::vector<Mesh::Face_index> selected;
    for (auto face : faces(mesh)) {
        auto h = halfedge(face, mesh);
        auto a = mesh.point(source(h,mesh));
        auto b = mesh.point(target(h,mesh));
        auto c = mesh.point(target(next(h,mesh),mesh));
        double x = (a.x()+b.x()+c.x())/3.0;
        double y = (a.y()+b.y()+c.y())/3.0;
        double r = std::hypot(x,y);
        if (r >= 83.0 && r < 87.0) selected.push_back(face);
    }
    std::cerr << "selected_faces " << selected.size() << '\n';
    PMP::isotropic_remeshing(selected, 0.6, mesh,
        CGAL::parameters::number_of_iterations(1).do_split(false)
        .do_collapse(false).do_flip(true)
        .number_of_relaxation_steps(0).do_project(false)
        .edge_is_constrained_map(constrained));
    if (!CGAL::is_valid_polygon_mesh(mesh) || !CGAL::is_closed(mesh)
        || mesh.number_of_faces() != faces_before
        || mesh.number_of_vertices() != vertices_before
        || CGAL::to_double(PMP::volume(mesh)) <= 0) return 4;
    if (!CGAL::IO::write_polygon_mesh(argv[2], mesh,
        CGAL::parameters::stream_precision(17))) return 5;
    std::cout << "selected_faces " << selected.size()
              << " constrained_edges " << constrained_count
              << " vertices " << mesh.number_of_vertices()
              << " faces " << mesh.number_of_faces()
              << " volume_before " << volume_before
              << " volume_after " << CGAL::to_double(PMP::volume(mesh)) << '\n';
    return 0;
}
