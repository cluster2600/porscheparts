// Direct tiny API witness only. No head input, simplification or physical claim.
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Surface_mesh.h>
#include <CGAL/Polyhedral_envelope.h>
#include <iostream>
#include <stdexcept>
#include <vector>

using Kernel=CGAL::Exact_predicates_inexact_constructions_kernel;
using Point=Kernel::Point_3;
using Mesh=CGAL::Surface_mesh<Point>;

int main(int argc,char**) {
  try {
    if(argc!=1)throw std::runtime_error("This fixed synthetic witness takes no arguments");
    Mesh reference;
    auto a=reference.add_vertex(Point(0,0,0));
    auto b=reference.add_vertex(Point(2,0,0));
    auto c=reference.add_vertex(Point(0,2,0));
    auto d=reference.add_vertex(Point(0,0,1));
    auto e=reference.add_vertex(Point(2,0,1));
    auto f=reference.add_vertex(Point(0,2,1));
    auto included=reference.add_face(a,b,c),omitted=reference.add_face(d,e,f);
    if(included==Mesh::null_face()||omitted==Mesh::null_face())
      throw std::runtime_error("Fixed reference triangles unavailable");
    const std::vector<Mesh::Face_index> selected{included};
    constexpr double epsilon=0.0625;
    const CGAL::Polyhedral_envelope<Kernel> full(reference,epsilon);
    const CGAL::Polyhedral_envelope<Kernel> subset(selected,reference,epsilon);
    const Point p(0.25,0.25,0),q(0.5,0.25,0),r(0.25,0.5,0);
    const Point u(0.25,0.25,1),v(0.5,0.25,1),w(0.25,0.5,1);
    const bool included_point=full(p)&&subset(p);
    const bool included_triangle=full(p,q,r)&&subset(p,q,r);
    const bool small_offset=subset(Point(0.25,0.25,0.015625));
    const bool omitted_point=full(u)&&!subset(u);
    const bool omitted_triangle=full(u,v,w)&&!subset(u,v,w);
    const bool outside_both=!full(Point(0.25,0.25,0.125))
                            &&!subset(Point(0.25,0.25,0.125));
    const bool passed=included_point&&included_triangle&&small_offset
                       &&omitted_point&&omitted_triangle&&outside_both;
    auto boolean=[](bool x){return x?"true":"false";};
    std::cout<<"{\"schema\":\"962-endpoint003-subset-envelope-witness/v1\","
      <<"\"epsilon_mm\":0.0625,\"reference_triangles\":2,\"subset_triangles\":1,"
      <<"\"included_point_accepted\":"<<boolean(included_point)
      <<",\"complete_included_triangle_accepted\":"<<boolean(included_triangle)
      <<",\"small_offset_point_accepted\":"<<boolean(small_offset)
      <<",\"omitted_point_full_accepts_subset_rejects\":"<<boolean(omitted_point)
      <<",\"complete_omitted_triangle_full_accepts_subset_rejects\":"<<boolean(omitted_triangle)
      <<",\"outside_point_rejected_by_both\":"<<boolean(outside_both)
      <<",\"passed\":"<<boolean(passed)
      <<",\"head_input_used\":false,\"solver_admission_established\":false,"
      <<"\"manufacturing_authorized\":false}"<<std::endl;
    return passed?0:2;
  } catch(const std::exception& error) {
    std::cerr<<"subset-envelope witness failure: "<<error.what()<<std::endl;
    return 2;
  }
}
