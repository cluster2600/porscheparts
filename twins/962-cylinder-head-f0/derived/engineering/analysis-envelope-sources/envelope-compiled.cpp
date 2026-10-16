// Separate analysis representation only. No source repair or engineering release.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polyhedral_envelope.h>
#include <CGAL/Surface_mesh_simplification/edge_collapse.h>
#include <CGAL/Surface_mesh_simplification/Edge_collapse_visitor_base.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/LindstromTurk_cost.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/LindstromTurk_placement.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Polyhedral_envelope_filter.h>
#include <CGAL/Surface_mesh_simplification/Policies/Edge_collapse/Bounded_normal_change_filter.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/version.h>
#include <array>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <unistd.h>

using Kernel = CGAL::Exact_predicates_inexact_constructions_kernel;
using Point = Kernel::Point_3;
using Mesh = CGAL::Surface_mesh<Point>;
namespace SMS = CGAL::Surface_mesh_simplification;
namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;
volatile std::sig_atomic_t stop_requested = 0;
void request_stop(int) { stop_requested = 1; }

template<class T> T read_value(std::istream& in) {
  T value;
  if (!in.read(reinterpret_cast<char*>(&value), sizeof(value)))
    throw std::runtime_error("Truncated binary indexed surface");
  return value;
}
template<class T> void write_value(std::ostream& out, T value) {
  out.write(reinterpret_cast<const char*>(&value), sizeof(value));
}

Mesh read_surface(const fs::path& path) {
  std::ifstream in(path, std::ios::binary);
  char magic[8];
  if (!in.read(magic, 8) || std::memcmp(magic, "962SURF1", 8))
    throw std::runtime_error("Expected exact binary64/uint64 indexed surface");
  auto nv = read_value<std::uint64_t>(in), nf = read_value<std::uint64_t>(in);
  if (!nv || !nf || nv > 2000000 || nf > 2000000 || fs::file_size(path) != 24+24*(nv+nf))
    throw std::runtime_error("Invalid indexed surface counts or byte length");
  Mesh mesh;
  mesh.reserve(nv, 3*nf/2, nf);
  std::vector<Mesh::Vertex_index> vertices;
  vertices.reserve(nv);
  for (std::uint64_t i=0; i<nv; ++i) {
    double x=read_value<double>(in), y=read_value<double>(in), z=read_value<double>(in);
    if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z))
      throw std::runtime_error("Nonfinite source coordinate");
    vertices.push_back(mesh.add_vertex(Point(x,y,z)));
  }
  for (std::uint64_t i=0; i<nf; ++i) {
    auto a=read_value<std::uint64_t>(in), b=read_value<std::uint64_t>(in), c=read_value<std::uint64_t>(in);
    if (a>=nv || b>=nv || c>=nv || a==b || b==c || c==a
        || CGAL::collinear(mesh.point(vertices[a]),mesh.point(vertices[b]),mesh.point(vertices[c]))
        || mesh.add_face(vertices[a],vertices[b],vertices[c]) == Mesh::null_face())
      throw std::runtime_error("Invalid, degenerate or nonmanifold indexed source face");
  }
  if (!CGAL::is_triangle_mesh(mesh) || !CGAL::is_closed(mesh) || !CGAL::is_valid_polygon_mesh(mesh))
    throw std::runtime_error("Closed valid oriented triangle mesh required");
  return mesh;
}

void write_surface(const Mesh& mesh, const fs::path& path) {
  if (fs::exists(path)) throw std::runtime_error("Existing surface output is preserved");
  std::ofstream out(path, std::ios::binary);
  out.write("962SURF1",8);
  write_value<std::uint64_t>(out,mesh.number_of_vertices());
  write_value<std::uint64_t>(out,mesh.number_of_faces());
  std::vector<std::uint64_t> ids(mesh.num_vertices(),std::uint64_t(-1));
  std::uint64_t i=0;
  for (auto v:mesh.vertices()) {
    ids[v.idx()]=i++;
    auto p=mesh.point(v);
    write_value<double>(out,CGAL::to_double(p.x()));
    write_value<double>(out,CGAL::to_double(p.y()));
    write_value<double>(out,CGAL::to_double(p.z()));
  }
  for (auto f:mesh.faces()) {
    auto h=mesh.halfedge(f);
    write_value<std::uint64_t>(out,ids[mesh.source(h).idx()]);
    write_value<std::uint64_t>(out,ids[mesh.target(h).idx()]);
    write_value<std::uint64_t>(out,ids[mesh.target(mesh.next(h)).idx()]);
  }
  out.close();
  if (!out) throw std::runtime_error("Surface output failed");
}

struct Deadline_only_stop {
  template<class FT,class Profile>
  bool operator()(const FT&, const Profile&, std::size_t, std::size_t) const {
    return stop_requested != 0;
  }
};

struct Checkpoints : SMS::Edge_collapse_visitor_base<Mesh> {
  Mesh* mesh;
  fs::path output;
  Clock::time_point* last;
  std::size_t* counter;
  void OnCollapsed(const Profile&,const vertex_descriptor&) {
    if (std::chrono::duration<double>(Clock::now()-*last).count() >= 30) {
      auto file=output/("checkpoint-"+std::to_string(++*counter)+".bin");
      write_surface(*mesh,file); *last=Clock::now();
      std::cout << "{\"stage\":\"checkpoint\",\"vertices\":" << mesh->number_of_vertices()
                << ",\"faces\":" << mesh->number_of_faces() << "}" << std::endl;
    }
  }
};

int self_test() {
  // The physical envelope must accept a near-plane query and reject far queries.
  Mesh plane;
  auto a=plane.add_vertex(Point(0,0,0)), b=plane.add_vertex(Point(4,0,0)), c=plane.add_vertex(Point(0,4,0));
  plane.add_face(a,b,c);
  CGAL::Polyhedral_envelope<Kernel> envelope(plane,.25);
  if (!envelope(Point(1,1,0)) || !envelope(Point(1,1,.1)) || envelope(Point(1,1,1))
      || !envelope(Point(.5,.5,0),Point(1,.5,0),Point(.5,1,0))
      || envelope(Point(.5,.5,0),Point(1,.5,0),Point(.5,1,1)))
    throw std::runtime_error("Known-result physical envelope queries failed");
  std::cout << "{\"status\":\"known_result_envelope_queries_passed\",\"query_count\":5,\"epsilon_mm\":0.25,\"CGAL\":\""
            << CGAL_VERSION_STR << "\"}" << std::endl;
  return 0;
}

int main(int argc,char** argv) {
  try {
    if (argc==2 && std::string(argv[1])=="--self-test") return self_test();
    if (argc!=5) throw std::runtime_error("Usage: cgal-envelope input.bin new-output epsilon-mm soft-deadline-s");
    const double epsilon=std::stod(argv[3]);
    const int deadline=std::stoi(argv[4]);
    if (epsilon!=.25 || deadline<1 || deadline>285) throw std::runtime_error("Predeclared0.25mm envelope and<=285s soft deadline required");
    fs::path output=argv[2];
    if (!fs::create_directory(output)) throw std::runtime_error("Output directory must be new");
    std::signal(SIGALRM,request_stop); std::signal(SIGTERM,request_stop); alarm(deadline);
    auto start=Clock::now();
    Mesh mesh=read_surface(argv[1]);
    write_surface(mesh,output/"before-collapse.bin");
    std::cout << "{\"stage\":\"source_imported_exact_indexed\",\"vertices\":" << mesh.number_of_vertices()
              << ",\"faces\":" << mesh.number_of_faces() << "}" << std::endl;
    using Filter=SMS::Polyhedral_envelope_filter<Kernel,SMS::Bounded_normal_change_filter<>>;
    Filter filter(epsilon);
    std::size_t checkpoints=0;
    auto last=Clock::now();
    Checkpoints visitor;
    visitor.mesh=&mesh; visitor.output=output; visitor.last=&last; visitor.counter=&checkpoints;
    auto removed=SMS::edge_collapse(mesh,Deadline_only_stop(),CGAL::parameters::get_cost(SMS::LindstromTurk_cost<Mesh>())
      .get_placement(SMS::LindstromTurk_placement<Mesh>()).filter(filter).visitor(visitor));
    write_surface(mesh,output/"surface.bin");
    alarm(0);
    std::cout << std::setprecision(17) << "{\"status\":\""
              << (stop_requested?"soft_deadline_partial_candidate_preserved":"admissible_collapses_exhausted_candidate_pending_audits")
              << "\",\"CGAL\":\"" << CGAL_VERSION_STR << "\",\"vertices\":" << mesh.number_of_vertices()
              << ",\"edges\":" << mesh.number_of_edges() << ",\"faces\":" << mesh.number_of_faces()
              << ",\"removed_edges\":" << removed << ",\"epsilon_mm\":" << epsilon
              << ",\"face_quota\":false,\"checkpoints\":" << checkpoints
              << ",\"closed\":" << (CGAL::is_closed(mesh)?"true":"false")
              << ",\"valid_polygon_mesh\":" << (CGAL::is_valid_polygon_mesh(mesh)?"true":"false")
              << ",\"wall_s\":" << std::chrono::duration<double>(Clock::now()-start).count()
              << ",\"engineering_accepted\":false}" << std::endl;
    return stop_requested?3:0;
  } catch (const std::exception& e) {
    std::cerr << "cgal-envelope failure: " << e.what() << std::endl;
    return 2;
  }
}
