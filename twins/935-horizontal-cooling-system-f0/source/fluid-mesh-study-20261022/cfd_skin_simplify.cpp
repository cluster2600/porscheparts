#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/detect_features.h>
#include <CGAL/Surface_mesh_simplification/edge_collapse.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Bounded_normal_change_filter.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Constrained_placement.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Polyhedral_envelope_filter.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Count_ratio_stop_predicate.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/LindstromTurk_cost.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/LindstromTurk_placement.h>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

using Kernel = CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<Kernel::Point_3>;
namespace SMS = CGAL::Surface_mesh_simplification;

double triangle_quality(const Kernel::Point_3& a, const Kernel::Point_3& b,
                        const Kernel::Point_3& c) {
    const auto ab = b-a, ac = c-a;
    const double denominator = ab.squared_length() + ac.squared_length() + (c-b).squared_length();
    if (!(denominator > 0) || !std::isfinite(denominator)) return 0;
    const double result = 2*std::sqrt(3*CGAL::cross_product(ab, ac).squared_length())/denominator;
    return std::isfinite(result) ? result : 0;
}

struct TriangleQualityFilter {
    template<class Profile>
    std::optional<typename Profile::Point> operator()(
            const Profile& profile, std::optional<typename Profile::Point> placement) const {
        if (!placement) return placement;
        auto triangle = profile.triangles().begin();
        if (profile.left_face_exists()) ++triangle;
        if (profile.right_face_exists()) ++triangle;
        // The collapsed vertex is v1 in every remaining profile triangle.
        for (; triangle != profile.triangles().end(); ++triangle) {
            const auto& points = profile.vertex_point_map();
            if (triangle_quality(get(points, triangle->v0), *placement,
                                 get(points, triangle->v2)) < 0.05)
                return std::nullopt;
        }
        return placement;
    }
};

struct FilterWitness {
    using Point = Kernel::Point_3;
    struct Triangle { Mesh::Vertex_index v0, v1, v2; };
    const Mesh& mesh;
    std::vector<Triangle> faces;
    const auto& triangles() const { return faces; }
    auto vertex_point_map() const { return get(CGAL::vertex_point, mesh); }
    bool left_face_exists() const { return true; }
    bool right_face_exists() const { return true; }
};

void self_test() {
    const Kernel::Point_3 a(0,0,0), b(1,0,0), c(.5,std::sqrt(3.)/2,0);
    if (std::abs(triangle_quality(a,b,c)-1) > 1e-14
            || std::abs(triangle_quality(a,b,Kernel::Point_3(0,1,0))-std::sqrt(3.)/2) > 1e-14
            || triangle_quality(a,b,Kernel::Point_3(.5,1e-8,0)) >= .05
            || triangle_quality(a,a,a) != 0
            || triangle_quality(a,b,Kernel::Point_3(.5,0,0)) != 0)
        throw std::runtime_error("triangle_quality_control_failed");
    Mesh mesh;
    const auto va = mesh.add_vertex(a), vb = mesh.add_vertex(b), vc = mesh.add_vertex(c);
    const FilterWitness profile{mesh, {{va,va,va}, {vb,vb,vb}, {va,vc,vb}}};
    const TriangleQualityFilter filter;
    if (!filter(profile, Kernel::Point_3(.5,1,0))
            || filter(profile, Kernel::Point_3(.5,1e-8,0))
            || filter(profile, std::nullopt))
        throw std::runtime_error("edge_profile_quality_filter_control_failed");
    std::cout << "five triangle controls and positive, needle and empty-placement profile controls passed\n";
}

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--self-test") { self_test(); return 0; }
    if (argc != 3 || std::filesystem::exists(std::filesystem::symlink_status(argv[2]))) return 2;
    Mesh mesh;
    if (!CGAL::IO::read_polygon_mesh(argv[1], mesh) || num_faces(mesh) == 0
            || num_faces(mesh) > 4000000 || !CGAL::is_triangle_mesh(mesh)
            || !CGAL::is_closed(mesh) || !CGAL::is_valid_polygon_mesh(mesh)) return 3;
    const auto initial = num_faces(mesh);
    auto constrained = mesh.add_property_map<Mesh::Edge_index,bool>("e:sharp",false).first;
    CGAL::Polygon_mesh_processing::detect_sharp_edges(mesh, 30., constrained);
    using Placement = SMS::Constrained_placement<SMS::LindstromTurk_placement<Mesh>, decltype(constrained)>;
    using NormalFilter = SMS::Bounded_normal_change_filter<TriangleQualityFilter>;
    SMS::Polyhedral_envelope_filter<Kernel, NormalFilter> filter(.02);
    const auto removed = SMS::edge_collapse(mesh, SMS::Count_ratio_stop_predicate<Mesh>(.6),
        CGAL::parameters::get_cost(SMS::LindstromTurk_cost<Mesh>())
            .get_placement(Placement(constrained)).edge_is_constrained_map(constrained).filter(filter));
    mesh.collect_garbage();
    if (!CGAL::is_closed(mesh) || !CGAL::is_valid_polygon_mesh(mesh)) return 4;
    if (!CGAL::IO::write_polygon_mesh(argv[2],mesh,CGAL::parameters::stream_precision(17))) return 5;
    std::cout << "{\"input_faces\":" << initial << ",\"output_faces\":" << num_faces(mesh)
        << ",\"removed_edges\":" << removed
        << ",\"new_face_quality_floor\":0.05,\"feature_angle_degrees\":30,\"generator_envelope_limit_mm\":0.02,"
           "\"complete_surface_distance_checked\":false,\"mechanical_mesh_admitted\":false}\n";
}
