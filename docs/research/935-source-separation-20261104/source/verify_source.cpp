// Independent full-source parser and connectivity verification, without welding.
#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct DSU {
  std::vector<std::int32_t> parent;
  std::vector<unsigned char> rank;
  explicit DSU(std::size_t n) : parent(n), rank(n, 0) {
    std::iota(parent.begin(), parent.end(), 0);
  }
  std::int32_t find(std::int32_t a) {
    while (parent[a] != a) {
      parent[a] = parent[parent[a]];
      a = parent[a];
    }
    return a;
  }
  void join(std::int32_t a, std::int32_t b) {
    a = find(a); b = find(b);
    if (a == b) return;
    if (rank[a] < rank[b] || (rank[a] == rank[b] && a > b)) std::swap(a, b);
    parent[b] = a;
    if (rank[a] == rank[b]) ++rank[a];
  }
  std::vector<std::int32_t> labels() {
    std::vector<std::int32_t> result(parent.size());
    for (std::size_t i = 0; i < result.size(); ++i) result[i] = find(i);
    return result;
  }
};

struct Edge { std::int64_t a, b; std::int32_t face; };

static std::string trim(const std::string& s) {
  const auto first = s.find_first_not_of(" \t\r\n");
  if (first == std::string::npos) return "";
  return s.substr(first, s.find_last_not_of(" \t\r\n") - first + 1);
}

static void save(const std::filesystem::path& path, const std::vector<std::int32_t>& values) {
  std::ofstream output(path, std::ios::binary);
  output.write(reinterpret_cast<const char*>(values.data()), values.size() * sizeof(values[0]));
  if (!output) throw std::runtime_error("Native label write failed");
}

int main(int argc, char** argv) {
  try {
    if (argc != 6) throw std::runtime_error("Expected faces, original OBJ, vertex count, face count, new output");
    std::uint16_t endian = 1;
    if (*reinterpret_cast<unsigned char*>(&endian) != 1) throw std::runtime_error("Little-endian host required");
    const auto nv = std::stoll(argv[3]), nf = std::stoll(argv[4]);
    if (nv < 1 || nf < 1 || nv > INT32_MAX || nf > INT32_MAX) throw std::runtime_error("Unsupported scope");
    std::vector<std::int64_t> faces(static_cast<std::size_t>(nf) * 3);
    std::ifstream input(argv[1], std::ios::binary);
    input.read(reinterpret_cast<char*>(faces.data()), faces.size() * sizeof(faces[0]));
    if (!input || input.peek() != std::char_traits<char>::eof()) throw std::runtime_error("Face binary size mismatch");
    for (auto v : faces) if (v < 0 || v >= nv) throw std::runtime_error("Invalid original vertex index");

    std::ifstream obj(argv[2]);
    if (!obj) throw std::runtime_error("Original OBJ unavailable");
    std::string line, object, group, material;
    std::map<std::string, std::int32_t> states;
    std::vector<std::int32_t> metadata;
    std::int64_t vertices_seen = 0, face = 0, objects = 0, groups = 0, materials = 0;
    while (std::getline(obj, line)) {
      const auto hash = line.find('#');
      if (hash != std::string::npos) line.resize(hash);
      std::istringstream row(line);
      std::string tag;
      if (!(row >> tag)) continue;
      if (tag == "v") ++vertices_seen;
      else if (tag == "o" || tag == "g" || tag == "usemtl") {
        std::string value; std::getline(row, value); value = trim(value);
        if (tag == "o") { object = value; ++objects; }
        if (tag == "g") { group = value; ++groups; }
        if (tag == "usemtl") { material = value; ++materials; }
      } else if (tag == "f") {
        if (face >= nf) throw std::runtime_error("Too many original OBJ faces");
        for (int k = 0; k < 3; ++k) {
          std::string token;
          if (!(row >> token)) throw std::runtime_error("Nontriangular original OBJ face");
          const auto slash = token.find('/');
          const std::string head = token.substr(0, slash);
          std::size_t consumed = 0;
          auto v = std::stoll(head, &consumed);
          if (consumed != head.size() || v == 0) throw std::runtime_error("Invalid raw OBJ index");
          v = v > 0 ? v - 1 : vertices_seen + v;
          if (v != faces[3 * face + k]) throw std::runtime_error("Original OBJ differs from frozen face binary");
        }
        std::string extra;
        if (row >> extra) throw std::runtime_error("Original OBJ face has extra corners");
        const auto key = object + std::string(1, '\0') + group + std::string(1, '\0') + material;
        const auto item = states.emplace(key, static_cast<std::int32_t>(states.size()));
        metadata.push_back(item.first->second);
        ++face;
      }
    }
    if (face != nf || vertices_seen != nv) throw std::runtime_error("Original OBJ scope mismatch");

    DSU vertex(nv), surface(nf);
    std::vector<Edge> edges;
    edges.reserve(static_cast<std::size_t>(nf) * 3);
    for (std::int32_t i = 0; i < nf; ++i) {
      vertex.join(faces[3*i], faces[3*i+1]);
      vertex.join(faces[3*i], faces[3*i+2]);
      for (int k = 0; k < 3; ++k) {
        auto a = faces[3*i+k], b = faces[3*i+(k+1)%3];
        if (a > b) std::swap(a, b);
        edges.push_back({a, b, i});
      }
    }
    std::sort(edges.begin(), edges.end(), [](const Edge& a, const Edge& b) {
      if (a.a != b.a) return a.a < b.a;
      if (a.b != b.b) return a.b < b.b;
      return a.face < b.face;
    });
    std::int64_t boundary = 0, unique = 0;
    for (std::size_t i = 0; i < edges.size();) {
      auto end = i + 1;
      while (end < edges.size() && edges[end].a == edges[i].a && edges[end].b == edges[i].b) ++end;
      if (end - i > 2) throw std::runtime_error("Nonmanifold original source edge");
      if (end - i == 2) surface.join(edges[i].face, edges[i+1].face);
      else ++boundary;
      ++unique; i = end;
    }
    const auto surface_labels = surface.labels(), vertex_labels = vertex.labels();
    const std::filesystem::path output(argv[5]);
    if (std::filesystem::exists(output)) throw std::runtime_error("Existing native output refused");
    std::filesystem::create_directory(output);
    save(output / "edge-face-labels.i32le", surface_labels);
    save(output / "vertex-labels.i32le", vertex_labels);
    save(output / "metadata-labels.i32le", metadata);
    std::ofstream report(output / "native.json");
    report << "{\n  \"face_edge_components\": " << std::set<std::int32_t>(surface_labels.begin(), surface_labels.end()).size()
           << ",\n  \"vertex_components_including_unused\": " << std::set<std::int32_t>(vertex_labels.begin(), vertex_labels.end()).size()
           << ",\n  \"unique_indexed_edges\": " << unique << ",\n  \"boundary_edges\": " << boundary
           << ",\n  \"face_bearing_metadata_states\": " << states.size()
           << ",\n  \"object_records\": " << objects << ",\n  \"group_records\": " << groups
           << ",\n  \"material_records\": " << materials
           << ",\n  \"all_raw_OBJ_face_indices_match\": true\n}\n";
    if (!report) throw std::runtime_error("Native report write failed");
    std::cout << "SOURCE_PARTITION_NATIVE_OK\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << "\n";
    return 2;
  }
}
