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

int main(int argc,char**argv){try{
 require(argc==3,"INPUT_DIRECTORY OUTPUT.json");std::string root=argv[1];auto parent=read_mesh((root+"/reference.mesh64").c_str());require(!PMP::does_self_intersect<CGAL::Sequential_tag>(parent),"Parent intersects itself");Tree parent_tree(faces(parent).first,faces(parent).second,parent);parent_tree.accelerate_distance_queries();CGAL::Side_of_triangle_mesh<Mesh,K> parent_side(parent);
 K::FT low[3],high[3];bool first=true;for(auto v:parent.vertices()){const auto&p=parent.point(v);for(int k=0;k<3;++k){if(first||p[k]<low[k])low[k]=p[k];if(first||p[k]>high[k])high[k]=p[k];}first=false;}
 Mesh control;append_tetra(control,0,0,0);CGAL::Side_of_triangle_mesh<Mesh,K> control_side(control);Tree control_tree(faces(control).first,faces(control).second,control);control_tree.accelerate_distance_queries();require(control_side(K::Point_3(K::FT(1)/8,K::FT(1)/8,K::FT(1)/8))==CGAL::ON_BOUNDED_SIDE&&control_side(K::Point_3(2,2,2))==CGAL::ON_UNBOUNDED_SIDE&&control_tree.squared_distance(K::Point_3(0,0,2))==1,"Bounded-side/distance controls failed");
 std::ofstream output(argv[2]);output<<std::setprecision(17)<<std::boolalpha<<"{\"status\":\"exact_cap_and_mouth_controls_passed\",\"CGAL_version\":\""<<CGAL_VERSION_STR<<"\",\"kernel\":\"EPECK\",\"analytic_controls_passed\":true,\"nominal_mouth_diameter_mm\":3,\"mouth_radius_numerical_allowance_mm\":0.0001,\"routes\":[";
 for(int i=0;i<8;++i){
  std::string suffix=std::to_string(i);auto own=read_mesh((root+"/own-"+suffix+".mesh64").c_str()),frustum=read_mesh((root+"/frustum-"+suffix+".mesh64").c_str()),tool=read_mesh((root+"/tool-"+suffix+".mesh64").c_str());require(!PMP::does_self_intersect<CGAL::Sequential_tag>(own)&&!PMP::does_self_intersect<CGAL::Sequential_tag>(frustum)&&!PMP::does_self_intersect<CGAL::Sequential_tag>(tool),"Control input self-intersects");
  std::ifstream params(root+"/params-"+suffix+".txt");double x[8];for(double&a:x){params>>a;require(bool(params)&&std::isfinite(a),"Finite route parameters required");}std::string extra;require(!(params>>extra)&&params.eof(),"Trailing route parameters");K::Point_3 p(x[0],x[1],x[2]);K::Vector_3 direction(x[3],x[4],x[5]);require(x[6]>0&&x[7]>x[6],"Positive flare and shaft lengths required");K::Point_3 end=p+direction*K::FT(x[7]);
  Tree own_tree(faces(own).first,faces(own).second,own);own_tree.accelerate_distance_queries();CGAL::Side_of_triangle_mesh<Mesh,K> own_side(own);require(own_side(p)==CGAL::ON_BOUNDED_SIDE&&parent_side(p)==CGAL::ON_BOUNDED_SIDE,"Entry centre lies outside its network or parent");
  K::FT entire_radius2=0,bottom_radius2=0;std::size_t bottom_count=0;for(auto v:frustum.vertices()){auto q=frustum.point(v);entire_radius2=std::max(entire_radius2,CGAL::squared_distance(p,q));if(std::abs(CGAL::to_double((q-p)*direction))<1e-6){++bottom_count;bottom_radius2=std::max(bottom_radius2,CGAL::squared_distance(p,q));}}
  require(bottom_count==64,"Exactly 64 entry-rim vertices required");auto own_distance2=own_tree.squared_distance(p),parent_distance2=parent_tree.squared_distance(p);require(own_distance2>bottom_radius2,"Entry cap does not fit wholly within its network");require(parent_distance2>entire_radius2,"Full flare is not inside the original parent");
  auto is_end=[&](Mesh::Vertex_index v){return CGAL::to_double((tool.point(v)-p)*direction)>x[7]-1e-6;};std::vector<K::Point_3> mouth;for(auto v:tool.vertices())if(is_end(v))mouth.push_back(tool.point(v));require(mouth.size()==64,"Exactly 64 mouth-rim vertices required");bool separated=false;for(int axis=0;axis<3;++axis){bool below=true,above=true;for(const auto&q:mouth){below=below&&q[axis]<low[axis];above=above&&q[axis]>high[axis];}separated=separated||below||above;}require(separated,"End cap is not wholly outside the parent bbox");
  auto cap_face=[&](Mesh::Face_index f){require(f!=Mesh::null_face(),"Open tool boundary");for(auto v:CGAL::vertices_around_face(tool.halfedge(f),tool))if(!is_end(v))return false;return true;};std::size_t rim_edges=0;K::FT minimum_radius2=0;
  for(auto e:tool.edges()){auto h=tool.halfedge(e);if(!is_end(tool.source(h))||!is_end(tool.target(h)))continue;if(cap_face(tool.face(h))==cap_face(tool.face(tool.opposite(h))))continue;auto radius2=CGAL::squared_distance(end,K::Segment_3(tool.point(tool.source(h)),tool.point(tool.target(h))));if(rim_edges++==0||radius2<minimum_radius2)minimum_radius2=radius2;}
  require(rim_edges==64,"Exactly 64 mouth perimeter edges required");K::FT threshold=K::FT(14999)/10000;require(minimum_radius2>=threshold*threshold,"Mouth aperture below nominal diameter outside numerical reserve");
  if(i)output<<",";output<<"{\"network\":"<<i<<",\"entry_cap_strictly_inside_own_network\":true,\"full_flare_strictly_inside_original_parent\":true,\"shaft_end_cap_outside_parent_bbox\":true,\"own_centre_clearance_mm\":"<<std::sqrt(CGAL::to_double(own_distance2))<<",\"parent_centre_clearance_mm\":"<<std::sqrt(CGAL::to_double(parent_distance2))<<",\"whole_flare_ball_radius_mm\":"<<std::sqrt(CGAL::to_double(entire_radius2))<<",\"mouth_minimum_perimeter_diameter_mm\":"<<2*std::sqrt(CGAL::to_double(minimum_radius2))<<",\"mouth_perimeter_edges\":"<<rim_edges<<"}";
 }output<<"],\"manufacturing_authorized\":false}\n";require(bool(output),"Output write failed");return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<std::endl;return 70;}}
