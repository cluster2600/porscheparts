// Read-only CGAL triangle-soup audit. No welding, orientation repair or export.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/version.h>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

int main(int argc, char** argv) {
  static_assert(std::endian::native == std::endian::little);
  static_assert(sizeof(double) == 8 && std::numeric_limits<double>::is_iec559);
  try {
    if(argc != 2) throw std::runtime_error("one_binary_input_required");
    std::ifstream in(argv[1], std::ios::binary);
    auto read = [&](auto& value) {
      if(!in.read(reinterpret_cast<char*>(&value), sizeof(value)))
        throw std::runtime_error("truncated_input");
    };
    std::array<char, 8> magic; read(magic);
    if(magic != std::array<char, 8>{'M','6','4','T','R','I','1','\0'})
      throw std::runtime_error("binary_format_required");
    std::uint64_t nv, nf; read(nv); read(nf);
    if(!nv || !nf || nv > 2000000 || nf > 2000000)
      throw std::runtime_error("bounded_counts_required");
    using Kernel = CGAL::Exact_predicates_inexact_constructions_kernel;
    std::vector<Kernel::Point_3> points; points.reserve(nv);
    for(std::uint64_t i=0; i<nv; ++i) {
      std::array<double,3> p; read(p);
      for(auto x:p) if(!std::isfinite(x)) throw std::runtime_error("finite_point_required");
      points.emplace_back(p[0],p[1],p[2]);
    }
    std::vector<std::array<std::size_t,3>> faces; faces.reserve(nf);
    for(std::uint64_t i=0; i<nf; ++i) {
      std::array<std::uint64_t,3> f; read(f);
      for(auto id:f) if(id>=nv) throw std::runtime_error("known_vertex_required");
      faces.push_back({f[0],f[1],f[2]});
    }
    if(in.peek()!=std::char_traits<char>::eof()) throw std::runtime_error("unexpected_trailing_data");
    std::vector<std::pair<std::size_t,std::size_t>> pairs;
    constexpr unsigned cap=100001;
    CGAL::Polygon_mesh_processing::triangle_soup_self_intersections<CGAL::Sequential_tag>(
      points, faces, std::back_inserter(pairs), CGAL::parameters::maximum_number(cap));
    std::cout << "{\"CGAL_version\":\"" << CGAL_VERSION_STR
      << "\",\"vertices\":" << nv << ",\"triangles\":" << nf
      << ",\"complete\":" << (pairs.size()<cap ? "true" : "false")
      << ",\"pairs_private\":[";
    for(std::size_t i=0; i<pairs.size(); ++i) {
      if(i) std::cout << ',';
      std::cout << '[' << pairs[i].first << ',' << pairs[i].second << ']';
    }
    std::cout << "]}\n";
  } catch(const std::exception& error) {
    std::cerr << error.what() << '\n'; return 2;
  }
}
