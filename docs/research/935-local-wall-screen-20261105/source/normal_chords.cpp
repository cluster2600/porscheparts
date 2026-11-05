// First non-source boundary hit along a declared ray; no wall qualification.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits_3.h>
#include <CGAL/AABB_triangle_primitive_3.h>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <variant>
#include <vector>

using K = CGAL::Exact_predicates_inexact_constructions_kernel;
using Triangles = std::vector<K::Triangle_3>;
using Primitive = CGAL::AABB_triangle_primitive_3<K, Triangles::const_iterator>;
using Tree = CGAL::AABB_tree<CGAL::AABB_traits_3<K, Primitive>>;

template<class T> std::vector<T> binary(const char* path, std::size_t count) {
    if (std::filesystem::file_size(path) != count * sizeof(T))
        throw std::runtime_error("Unexpected input byte count");
    std::ifstream stream(path, std::ios::binary);
    std::vector<T> value(count);
    stream.read(reinterpret_cast<char*>(value.data()), count * sizeof(T));
    if (!stream) throw std::runtime_error("Binary input read failed");
    return value;
}

int main(int argc, char** argv) {
    try {
        if (argc != 8) throw std::runtime_error("Expected vertices faces Nv Nf queries output report");
        if (std::filesystem::exists(argv[6]) || std::filesystem::exists(argv[7]))
            throw std::runtime_error("Existing output refused");
        std::size_t nv = std::stoull(argv[3]), nf = std::stoull(argv[4]);
        auto vertices = binary<std::array<double,3>>(argv[1], nv);
        auto faces = binary<std::array<std::int64_t,3>>(argv[2], nf);
        for (const auto& vertex : vertices)
            for (auto scalar : vertex) if (!std::isfinite(scalar))
                throw std::runtime_error("Nonfinite input vertex");
        Triangles triangles;
        triangles.reserve(nf);
        for (const auto& face : faces) {
            for (auto index : face) if (index < 0 || std::size_t(index) >= nv)
                throw std::runtime_error("Invalid input index");
            const auto& a=vertices[face[0]]; const auto& b=vertices[face[1]]; const auto& c=vertices[face[2]];
            triangles.emplace_back(K::Point_3(a[0],a[1],a[2]), K::Point_3(b[0],b[1],b[2]), K::Point_3(c[0],c[1],c[2]));
            if (triangles.back().is_degenerate()) throw std::runtime_error("Degenerate input refused");
        }
        Tree tree(triangles.cbegin(), triangles.cend()); tree.build();
        std::ifstream queries(argv[5]); std::size_t count;
        if (!(queries >> count) || !count) throw std::runtime_error("Invalid query count");
        std::ofstream output(argv[6]); output << std::setprecision(17);
        std::size_t missed=0, nonpoint=0;
        for (std::size_t i=0; i<count; ++i) {
            std::int64_t source; double x,y,z,dx,dy,dz;
            if (!(queries >> source >> x >> y >> z >> dx >> dy >> dz) || source < -1 || source >= std::int64_t(nf))
                throw std::runtime_error("Invalid ray row");
            for (auto scalar : {x,y,z,dx,dy,dz}) if (!std::isfinite(scalar))
                throw std::runtime_error("Nonfinite ray refused");
            K::Vector_3 direction(dx,dy,dz);
            if (direction.squared_length()==0) throw std::runtime_error("Zero ray refused");
            auto hit = tree.first_intersection(K::Ray_3(K::Point_3(x,y,z),direction),
                [&](Triangles::const_iterator id){return id-triangles.cbegin()==source;});
            if (!hit) {++missed; output << i << " -1 0 0 0\n"; continue;}
            const auto* point=std::get_if<K::Point_3>(&hit->first);
            if (!point) {++nonpoint; output << i << " -2 0 0 0\n"; continue;}
            output << i << ' ' << hit->second-triangles.cbegin() << ' '
                   << point->x() << ' ' << point->y() << ' ' << point->z() << '\n';
        }
        std::string extra; if (queries >> extra) throw std::runtime_error("Trailing query data refused");
        output.close(); if (!output) throw std::runtime_error("Output write failed");
        std::ofstream report(argv[7]);
        report << "{\"queries\":" << count << ",\"missed\":" << missed
               << ",\"nonpoint\":" << nonpoint << ",\"physical_wall_qualification\":false}\n";
        report.close(); if (!report) throw std::runtime_error("Report write failed");
        std::cout << "NORMAL_CHORD_QUERIES_FINISHED\n";
    } catch(const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
