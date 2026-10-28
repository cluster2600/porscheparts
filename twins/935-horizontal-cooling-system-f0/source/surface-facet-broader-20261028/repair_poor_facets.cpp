#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/IO/polygon_mesh_io.h>
#include <CGAL/Polygon_mesh_processing/connected_components.h>
#include <CGAL/Polygon_mesh_processing/measure.h>
#include <CGAL/Polygon_mesh_processing/repair_degeneracies.h>
#include <CGAL/version.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <vector>

using K = CGAL::Exact_predicates_inexact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;
using Face = Mesh::Face_index;
using VC = Mesh::Property_map<Mesh::Vertex_index, bool>;
using EC = Mesh::Property_map<Mesh::Edge_index, bool>;
namespace PMP = CGAL::Polygon_mesh_processing;

double quality(K::Point_3 a, K::Point_3 b, K::Point_3 c) {
    auto ab = b-a, ac = c-a, bc = c-b;
    const double sum = ab.squared_length()+ac.squared_length()+bc.squared_length();
    if (!(sum > 0) || !std::isfinite(sum)) return 0;
    const double q = 2*std::sqrt(3*CGAL::cross_product(ab,ac).squared_length())/sum;
    return std::isfinite(q) ? q : 0;
}

std::array<Mesh::Vertex_index,3> corners(Face f, const Mesh& mesh) {
    auto h = halfedge(f,mesh);
    return {source(h,mesh),target(h,mesh),target(next(h,mesh),mesh)};
}

std::vector<Face> poor_faces(const Mesh& mesh) {
    std::vector<Face> result;
    for (auto f : faces(mesh)) {
        auto v = corners(f,mesh);
        if (quality(mesh.point(v[0]),mesh.point(v[1]),mesh.point(v[2])) < .05) result.push_back(f);
    }
    return result;
}

bool repair(Mesh& mesh, const std::vector<Face>& selected, VC vertices, EC edges, double limit=.001) {
    return PMP::remove_almost_degenerate_faces(selected,mesh,
        CGAL::parameters::needle_threshold(25.).cap_threshold(-.99026806874157036)
        .collapse_length_threshold(limit).flip_triangle_height_threshold(std::min(limit,.01))
        .vertex_is_constrained_map(vertices).edge_is_constrained_map(edges)
        .filter([](K::Point_3 a,K::Point_3 b,K::Point_3 c) { return quality(a,b,c) >= .05; }));
}

long long euler(const Mesh& mesh) {
    return static_cast<long long>(mesh.number_of_vertices())-static_cast<long long>(mesh.number_of_edges())+static_cast<long long>(mesh.number_of_faces());
}

std::size_t components(Mesh& mesh) {
    auto map = mesh.add_property_map<Face,std::size_t>("f:component",0).first;
    return PMP::connected_components(mesh,map);
}

Mesh needle_tetrahedron() {
    Mesh mesh;
    std::vector<Mesh::Vertex_index> v;
    for (auto p : std::vector<K::Point_3>{{0,0,0},{1,0,0},{0,1,0},{0,0,1},{1-1e-6,0,0}}) v.push_back(mesh.add_vertex(p));
    for (auto f : std::vector<std::array<int,3>>{{1,2,3},{0,3,2},{0,4,3},{4,1,3},{0,2,4},{4,2,1}})
        if (mesh.add_face(v[f[0]],v[f[1]],v[f[2]]) == Mesh::null_face()) throw std::runtime_error("invalid_control_fixture");
    return mesh;
}

Mesh broader_needle_tetrahedron() {
    Mesh mesh;
    std::vector<Mesh::Vertex_index> v;
    for (auto p : std::vector<K::Point_3>{{0,0,0},{.1,0,0},{0,.1,0},{0,0,.1},{.0951,0,0}})
        v.push_back(mesh.add_vertex(p));
    for (auto f : std::vector<std::array<int,3>>{{1,2,3},{0,3,2},{0,4,3},{4,1,3},{0,2,4},{4,2,1}})
        if (mesh.add_face(v[f[0]],v[f[1]],v[f[2]]) == Mesh::null_face())
            throw std::runtime_error("invalid_broader_control_fixture");
    return mesh;
}

void self_test(double limit) {
    if (std::abs(quality({0,0,0},{1,0,0},{.5,std::sqrt(3.)/2,0})-1) > 1e-12
        || quality({0,0,0},{1,0,0},{.5,0,0}) != 0
        || quality({0,0,0},{1,0,0},{.5,1e-8,0}) >= .05) throw std::runtime_error("triangle_filter_control_failed");
    // This analytic facet is below the quality floor but lies between the old
    // 35:1 and the new 25:1 needle thresholds.
    const K::Point_3 a(0,0,0), b(.014,0,0), c(-.25,.32,0);
    const double lengths[] = {(b-a).squared_length(), (c-b).squared_length(), (a-c).squared_length()};
    const double ratio = std::sqrt(*std::max_element(lengths,lengths+3) / *std::min_element(lengths,lengths+3));
    if (!(quality(a,b,c)<.05 && ratio>25. && ratio<35.))
        throw std::runtime_error("broader_classifier_fixture_failed");
    if (limit >= .005) {
        auto broad = broader_needle_tetrahedron();
        auto bvc = broad.add_property_map<Mesh::Vertex_index,bool>("v:fixed",false).first;
        auto bec = broad.add_property_map<Mesh::Edge_index,bool>("e:fixed",false).first;
        for (auto v : vertices(broad)) put(bvc,v,v.idx()<4);
        for (auto e : edges(broad)) {
            auto h=halfedge(e,broad);
            put(bec,e,get(bvc,source(h,broad))&&get(bvc,target(h,broad)));
        }
        const auto before = poor_faces(broad).size();
        repair(broad,poor_faces(broad),bvc,bec,limit);
        broad.collect_garbage();
        if (before != 2 || !poor_faces(broad).empty() || broad.number_of_faces()!=4
            || !CGAL::is_closed(broad) || components(broad)!=1
            || std::abs(CGAL::to_double(PMP::volume(broad))-.001/6)>1e-12)
            throw std::runtime_error("broader_needle_repair_control_failed");
    }
    auto mesh = needle_tetrahedron();
    auto vc = mesh.add_property_map<Mesh::Vertex_index,bool>("v:fixed",false).first;
    auto ec = mesh.add_property_map<Mesh::Edge_index,bool>("e:fixed",false).first;
    for (auto v : vertices(mesh)) put(vc,v,v.idx()<4);
    for (auto e : edges(mesh)) { auto h=halfedge(e,mesh);put(ec,e,get(vc,source(h,mesh))&&get(vc,target(h,mesh))); }
    const auto before = poor_faces(mesh).size();
    repair(mesh,poor_faces(mesh),vc,ec,limit);
    mesh.collect_garbage();
    if (before != 2 || !poor_faces(mesh).empty() || mesh.number_of_faces()!=4 || euler(mesh)!=2
        || !CGAL::is_closed(mesh) || components(mesh)!=1 || std::abs(CGAL::to_double(PMP::volume(mesh))-1./6)>1e-12)
        throw std::runtime_error("analytic_needle_repair_control_failed");
    auto fixed = needle_tetrahedron();
    auto fvc = fixed.add_property_map<Mesh::Vertex_index,bool>("v:fixed",true).first;
    auto fec = fixed.add_property_map<Mesh::Edge_index,bool>("e:fixed",true).first;
    repair(fixed,poor_faces(fixed),fvc,fec,limit);
    if (fixed.number_of_faces()!=6 || poor_faces(fixed).size()!=2 || euler(fixed)!=2)
        throw std::runtime_error("constrained_refusal_control_failed");
    std::cout << "triangle, exact-plane unit-volume needle and constrained-refusal controls passed\n";
}

int main(int argc,char** argv) {
    try {
        if (argc==2 && std::string(argv[1])=="--self-test") {for (double limit : {.001,.005,.01,.02,.05}) self_test(limit);return 0;}
        if ((argc!=3 && argc!=4) || std::filesystem::exists(std::filesystem::symlink_status(argv[2]))) return 2;
        double limit=.001;
        if (argc==4) {
            std::size_t consumed=0;limit=std::stod(argv[3],&consumed);
            if (consumed!=std::string(argv[3]).size() || !std::isfinite(limit) || (limit!=.001 && limit!=.005 && limit!=.01 && limit!=.02 && limit!=.05)) return 2;
        }
        if (std::filesystem::file_size(argv[1]) > 512ULL*1024*1024) return 2;
        Mesh mesh;
        if (!CGAL::IO::read_polygon_mesh(argv[1],mesh) || !CGAL::is_triangle_mesh(mesh)
            || !CGAL::is_valid_polygon_mesh(mesh) || !CGAL::is_closed(mesh)
            || mesh.number_of_vertices()<4 || mesh.number_of_vertices()>2000000 || mesh.number_of_faces()>4000000
            || components(mesh)!=1) return 3;
        const auto chi=euler(mesh), original_vertices=static_cast<long long>(mesh.number_of_vertices());
        const auto original_faces=mesh.number_of_faces();
        const double volume_before=CGAL::to_double(PMP::volume(mesh));
        if (!(volume_before>0) || !std::isfinite(volume_before)) return 3;
        auto selected=poor_faces(mesh);
        std::vector<unsigned char> eligible(original_vertices,0);
        for (auto f : selected) for (auto v : corners(f,mesh)) eligible[v.idx()]=1;
        for (int ring=0;ring<3;++ring) {
            auto next=eligible;
            for (auto e : edges(mesh)) {auto h=halfedge(e,mesh);auto a=source(h,mesh).idx(),b=target(h,mesh).idx();if (eligible[a]||eligible[b]) next[a]=next[b]=1;}
            eligible.swap(next);
        }
        auto ids=mesh.add_property_map<Mesh::Vertex_index,std::size_t>("v:original",0).first;
        auto vc=mesh.add_property_map<Mesh::Vertex_index,bool>("v:fixed",false).first;
        auto ec=mesh.add_property_map<Mesh::Edge_index,bool>("e:fixed",false).first;
        std::vector<K::Point_3> original_points(original_vertices);
        for (auto v : vertices(mesh)) {put(ids,v,v.idx());put(vc,v,!eligible[v.idx()]);original_points[v.idx()]=mesh.point(v);}
        for (auto e : edges(mesh)) {auto h=halfedge(e,mesh);put(ec,e,!eligible[source(h,mesh).idx()]||!eligible[target(h,mesh).idx()]);}
        auto outside_faces = [&](const Mesh& m) {
            std::vector<std::array<std::size_t,3>> result;
            for (auto f : faces(m)) {
                auto v=corners(f,m);std::array<std::size_t,3> key{get(ids,v[0]),get(ids,v[1]),get(ids,v[2])};
                if (!eligible[key[0]]&&!eligible[key[1]]&&!eligible[key[2]]) {std::sort(key.begin(),key.end());result.push_back(key);}
            }
            std::sort(result.begin(),result.end());return result;
        };
        const auto outside_before=outside_faces(mesh);
        const bool algorithm_reports_complete=repair(mesh,selected,vc,ec,limit);
        std::vector<bool> seen(original_vertices,false);
        for (auto v : vertices(mesh)) {
            auto id=get(ids,v);if (id>=original_points.size()) throw std::runtime_error("unexpected_vertex_identity");
            seen[id]=true;if (!eligible[id] && mesh.point(v)!=original_points[id]) throw std::runtime_error("fixed_point_changed");
        }
        for (std::size_t i=0;i<seen.size();++i) if (!eligible[i]&&!seen[i]) throw std::runtime_error("fixed_point_removed");
        if (outside_faces(mesh)!=outside_before) throw std::runtime_error("outside_faces_changed");
        mesh.collect_garbage();
        const auto remaining=poor_faces(mesh).size();
        const double volume_after=CGAL::to_double(PMP::volume(mesh));
        if (!CGAL::is_valid_polygon_mesh(mesh)||!CGAL::is_closed(mesh)||euler(mesh)!=chi||components(mesh)!=1
            || !(volume_after>0)||!std::isfinite(volume_after)) return 4;
        if (!CGAL::IO::write_polygon_mesh(argv[2],mesh,CGAL::parameters::stream_precision(17))) return 5;
        std::cout << "{\"CGAL\":\"" << CGAL_VERSION_STR << "\",\"input_vertices\":" << original_vertices
            << ",\"input_faces\":" << original_faces << ",\"input_poor_faces\":" << selected.size()
            << ",\"output_vertices\":" << mesh.number_of_vertices() << ",\"output_faces\":" << mesh.number_of_faces()
            << ",\"output_poor_faces\":" << remaining
            << ",\"needle_threshold_ratio\":25,\"cap_threshold_degrees\":172"
            << ",\"Euler_characteristic_before\":" << chi
            << ",\"Euler_characteristic_after\":" << euler(mesh) << ",\"connected_components\":1"
            << ",\"algorithm_reports_complete\":" << (algorithm_reports_complete?"true":"false")
            << ",\"outside_patch_vertices_and_faces_unchanged\":true,\"patch_rings\":3"
            << ",\"new_triangle_quality_floor\":0.05,\"collapse_length_limit_native_units\":" << limit
            << ",\"flip_height_limit_native_units\":" << std::min(limit,.01) << ",\"complete_surface_bound_established\":false"
            << ",\"CFD_accepted\":false,\"manufacturing_authorized\":false}\n";
        return 0;
    } catch (const std::exception& error) {std::cerr << error.what() << '\n';return 6;}
}
