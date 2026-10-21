// Inspect the actual compiled Adamantine STL activation predicate; no physics solve.
#include <Geometry.hh>
#include <deal.II/base/mpi.h>
#include <deal.II/fe/fe_q.h>
#include <boost/property_tree/info_parser.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <set>
#include <vector>

int main(int argc, char **argv)
{
  dealii::Utilities::MPI::MPI_InitFinalize mpi(argc, argv, 1);
  if (argc != 4)
    throw std::runtime_error("Expected geometry.info report.json occupied-cells.csv");
  boost::property_tree::ptree input, report;
  boost::property_tree::read_info(argv[1], input);
  auto const &units = input.get_child("units");
  boost::optional<boost::property_tree::ptree const &> optional_units(units);
  adamantine::Geometry<3> geometry(MPI_COMM_WORLD, input.get_child("geometry"), optional_units);
  auto &triangulation = geometry.get_triangulation();
  dealii::DoFHandler<3> dofs(triangulation);
  dealii::FE_Q<3> fe(1);
  dofs.distribute_dofs(fe);
  std::vector<bool> within(triangulation.n_active_cells(), false);
  std::vector<unsigned int> parent(within.size());
  std::iota(parent.begin(), parent.end(), 0);
  auto root = [&](unsigned int n) {
    while (parent[n] != n) { parent[n] = parent[parent[n]]; n = parent[n]; }
    return n;
  };
  std::ofstream cells(argv[3]);
  cells << "cell,x_mm,y_mm,z_mm,volume_mm3\n" << std::setprecision(17);
  double volume = 0, maximum_edge = 0;
  unsigned int count = 0;
  for (auto const &cell : dofs.active_cell_iterators())
  {
    auto const id = cell->active_cell_index();
    within[id] = geometry.is_within_stl(cell);
    if (within[id])
    {
      ++count;
      volume += cell->measure() * 1e9;
      cells << id;
      for (unsigned int d = 0; d < 3; ++d) cells << ',' << cell->center()[d] * 1000;
      cells << ',' << cell->measure() * 1e9 << '\n';
      for (unsigned int edge = 0; edge < 12; ++edge)
        maximum_edge = std::max(maximum_edge, cell->line(edge)->diameter() * 1000);
    }
  }
  for (auto const &cell : dofs.active_cell_iterators())
    if (within[cell->active_cell_index()])
      for (unsigned int face = 0; face < 6; ++face)
        if (!cell->at_boundary(face))
        {
          auto const neighbor = cell->neighbor(face)->active_cell_index();
          if (within[neighbor]) parent[root(neighbor)] = root(cell->active_cell_index());
        }
  std::set<unsigned int> components;
  for (unsigned int i = 0; i < within.size(); ++i) if (within[i]) components.insert(root(i));
  report.put("status", "native_geometry_occupation_completed_no_physics");
  report.put("background_hexahedra", within.size());
  report.put("occupied_hexahedra", count);
  report.put("occupied_face_connected_components", components.size());
  report.put("occupied_volume_mm3", volume);
  report.put("maximum_occupied_cell_edge_mm", maximum_edge);
  report.put("stl_triangles", geometry.get_stl_triangles().extent(0));
  report.put("thermal_steps", 0);
  report.put("mechanical_solves", 0);
  boost::property_tree::write_json(argv[2], report);
  std::cout << "Native carrier occupation done: " << count << " occupied cells\n";
}
