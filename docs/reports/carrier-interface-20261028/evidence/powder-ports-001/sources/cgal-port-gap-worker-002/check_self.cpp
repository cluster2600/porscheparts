#include <CGAL/Side_of_triangle_mesh.h>
#include <CGAL/Polygon_mesh_processing/connected_components.h>
// Independent exact-predicate self-intersection checks on complete binary64 triangle meshes.
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Polygon_mesh_processing/self_intersections.h>
#include <CGAL/AABB_tree.h>
#include <CGAL/AABB_traits.h>
#include <CGAL/AABB_face_graph_triangle_primitive.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/boost/graph/helpers.h>
#include <CGAL/number_utils.h>
#include <CGAL/version.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>
#include <vector>

using K = CGAL::Exact_predicates_exact_constructions_kernel;
using Mesh = CGAL::Surface_mesh<K::Point_3>;
namespace PMP = CGAL::Polygon_mesh_processing;

void require(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}

std::size_t index_token(std::istream& input) {
  std::string token;
  input >> token;
  require(bool(input) && !token.empty() && token.find_first_not_of("0123456789") == std::string::npos,
          "A nonnegative decimal integer is required");
  const unsigned long long n = std::stoull(token);
  require(n <= std::numeric_limits<std::size_t>::max(), "Index overflow");
  return static_cast<std::size_t>(n);
}

Mesh read_mesh(const char* filename) {
  // Existing native mesh64 transport: decimal17 IEEE coordinates, then integer rows.
  // A future encoder must prove binary64 roundtrip against the actual NPZ/STL arrays.
  std::ifstream input(filename);
  input.imbue(std::locale::classic());
  require(bool(input), "Cannot open the frozen mesh transport");
  const auto nv = index_token(input), nf = index_token(input);
  require(nv > 0 && nf > 0, "A nonempty mesh is required");
  Mesh mesh;
  std::vector<Mesh::Vertex_index> vertices;
  std::vector<bool> used(nv, false);
  vertices.reserve(nv);
  for (std::size_t i = 0; i < nv; ++i) {
    double x, y, z;
    input >> x >> y >> z;
    require(bool(input) && std::isfinite(x) && std::isfinite(y) && std::isfinite(z),
            "Finite binary64 coordinates are required");
    // Parse to double first. FT(double) preserves its exact dyadic value.
    vertices.push_back(mesh.add_vertex(K::Point_3(K::FT(x), K::FT(y), K::FT(z))));
  }
  for (std::size_t i = 0; i < nf; ++i) {
    const std::array<std::size_t, 3> row{{index_token(input), index_token(input), index_token(input)}};
    require(row[0] < nv && row[1] < nv && row[2] < nv &&
            row[0] != row[1] && row[1] != row[2] && row[0] != row[2], "Invalid triangle indices");
    const auto a = vertices[row[0]], b = vertices[row[1]], c = vertices[row[2]];
    require(!CGAL::collinear(mesh.point(a), mesh.point(b), mesh.point(c)),
            "An exactly zero-area triangle is forbidden");
    require(mesh.add_face(a, b, c) != Mesh::null_face(),
            "Face insertion failed; no automatic orientation or topology repair is permitted");
    for (const auto v : row) used[v] = true;
  }
  input >> std::ws;
  require(input.eof(), "Unexpected trailing mesh data");
  for (const bool present : used) require(present, "Unused input vertex");
  require(mesh.number_of_vertices() == nv && mesh.number_of_faces() == nf &&
          CGAL::is_triangle_mesh(mesh) && CGAL::is_closed(mesh) && CGAL::is_valid_polygon_mesh(mesh),
          "One complete closed oriented triangular transport is required");
  return mesh;
}


void append_tetra(Mesh& mesh, K::FT x, K::FT y, K::FT z) {
  auto a=mesh.add_vertex(K::Point_3(x,y,z));
  auto b=mesh.add_vertex(K::Point_3(x+1,y,z));
  auto c=mesh.add_vertex(K::Point_3(x,y+1,z));
  auto d=mesh.add_vertex(K::Point_3(x,y,z+1));
  mesh.add_face(a,c,b);mesh.add_face(a,b,d);mesh.add_face(a,d,c);mesh.add_face(b,c,d);
}

using Primitive=CGAL::AABB_face_graph_triangle_primitive<Mesh>;
using Traits=CGAL::AABB_traits<K,Primitive>;
using Tree=CGAL::AABB_tree<Traits>;

struct GapResult { bool pass=true; std::size_t vertices=0,centres=0,leaves=0; unsigned depth=0; };
K::Point_3 midpoint(const K::Point_3&a,const K::Point_3&b){return K::Point_3((a.x()+b.x())/2,(a.y()+b.y())/2,(a.z()+b.z())/2);}
GapResult certify(const Mesh&source,Tree&target){
 GapResult r; const K::FT g=K::FT(10001)/10000,g2=g*g;
 for(auto v:source.vertices()){++r.vertices;if(target.squared_distance(source.point(v))<g2){r.pass=false;return r;}}
 struct T{K::Point_3 a,b,c;unsigned depth;};std::vector<T> pending;
 for(auto f:source.faces()){auto h=source.halfedge(f);pending.push_back({source.point(source.source(h)),source.point(source.target(h)),source.point(source.target(source.next(h))),0});}
 while(!pending.empty()){
  auto t=pending.back();pending.pop_back();r.depth=std::max(r.depth,t.depth);require(++r.centres<=500000,"Exact-query budget exceeded");
  K::Point_3 p((t.a.x()+t.b.x()+t.c.x())/3,(t.a.y()+t.b.y()+t.c.y())/3,(t.a.z()+t.b.z()+t.c.z())/3);
  auto d2=target.squared_distance(p);if(d2<g2){r.pass=false;return r;}
  K::FT radius2=std::max({CGAL::squared_distance(p,t.a),CGAL::squared_distance(p,t.b),CGAL::squared_distance(p,t.c)});K::FT l=d2-radius2-g2;
  if(l>=0&&l*l>=4*g2*radius2){++r.leaves;continue;}
  require(t.depth<12,"All-face refinement depth exceeded");auto ab=midpoint(t.a,t.b),bc=midpoint(t.b,t.c),ca=midpoint(t.c,t.a);auto n=t.depth+1;
  pending.push_back({t.a,ab,ca,n});pending.push_back({ab,t.b,bc,n});pending.push_back({ca,bc,t.c,n});pending.push_back({ab,bc,ca,n});
 }return r;
}
int main(int argc,char**argv){try{
 require(argc==4,"PORT.mesh64 OTHER_SEVEN.mesh64 OUTPUT.json");Mesh control,separate,close;append_tetra(control,0,0,0);append_tetra(separate,3,0,0);append_tetra(close,K::FT(3)/2,0,0);Tree far_tree(faces(separate).first,faces(separate).second,separate),close_tree(faces(close).first,faces(close).second,close);far_tree.accelerate_distance_queries();close_tree.accelerate_distance_queries();require(certify(control,far_tree).pass&&!certify(control,close_tree).pass,"Exact all-face controls failed");
 auto source=read_mesh(argv[1]),target=read_mesh(argv[2]);require(!PMP::does_self_intersect<CGAL::Sequential_tag>(source)&&!PMP::does_self_intersect<CGAL::Sequential_tag>(target),"Intersecting source or target");
 auto source_components=source.add_property_map<Mesh::Face_index,std::size_t>("f:source_component",0).first;require(PMP::connected_components(source,source_components)==1,"Exactly one source component required");
 auto components=target.add_property_map<Mesh::Face_index,std::size_t>("f:component",0).first;auto count=PMP::connected_components(target,components);require(count==7,"Exactly seven target components required");
 CGAL::Side_of_triangle_mesh<Mesh,K> source_side(source),target_side(target);require(target_side(source.point(*source.vertices().begin()))==CGAL::ON_UNBOUNDED_SIDE,"Port boundary lies inside another network");std::vector<bool> visited(count,false);for(auto f:target.faces()){auto k=components[f];if(visited[k])continue;require(source_side(target.point(target.source(target.halfedge(f))))==CGAL::ON_UNBOUNDED_SIDE,"Port encloses another network");visited[k]=true;}
 Tree tree(faces(target).first,faces(target).second,target);tree.accelerate_distance_queries();auto r=certify(source,tree);
 std::ofstream out(argv[3]);out<<std::setprecision(17)<<std::boolalpha<<"{\"status\":\""<<(r.pass?"exact_all_face_gap_certificate_passed":"exact_gap_witness_refused")<<"\",\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPECK\",\"controls_passed\":true,\"gap_threshold_exact_mm\":\"10001/10000\",\"all_source_faces_covered\":"<<r.pass<<",\"source_faces\":"<<source.number_of_faces()<<",\"target_faces\":"<<target.number_of_faces()<<",\"target_components\":"<<count<<",\"vertex_queries\":"<<r.vertices<<",\"exact_centroid_queries\":"<<r.centres<<",\"accepted_cover_triangles\":"<<r.leaves<<",\"maximum_refinement_depth\":"<<r.depth<<",\"containment_exclusions_passed\":true,\"manufacturing_authorized\":false}\n";require(bool(out),"Output write failed");return r.pass?0:3;
}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 70;}}
