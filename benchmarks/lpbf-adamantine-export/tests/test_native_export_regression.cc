/* SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception */
#include <PostProcessor.hh>

#include <deal.II/base/mpi.h>
#include <deal.II/distributed/tria.h>
#include <deal.II/fe/fe_dgq.h>
#include <deal.II/fe/fe_q.h>
#include <deal.II/fe/fe_system.h>
#include <deal.II/grid/grid_generator.h>

#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>

int main(int argc, char **argv)
{
  try
  {
    if (argc != 2)
      throw std::runtime_error("usage: export_regression NEW_OUTPUT_DIRECTORY");
    dealii::Utilities::MPI::MPI_InitFinalize mpi(argc, argv, 1);
    if (dealii::Utilities::MPI::n_mpi_processes(MPI_COMM_WORLD) != 1)
      throw std::runtime_error(
          "this one-cell regression requires one MPI rank");
    std::filesystem::path const output = std::filesystem::absolute(argv[1]);
    if (!std::filesystem::create_directory(output))
      throw std::runtime_error("output must be a new directory");

    dealii::parallel::distributed::Triangulation<3> mesh(MPI_COMM_WORLD);
    dealii::GridGenerator::hyper_cube(mesh);
    dealii::FE_Q<3> thermal_fe(1);
    dealii::FESystem<3> mechanical_fe(thermal_fe, 3);
    dealii::FE_DGQ<3> material_fe(0);
    dealii::DoFHandler<3> thermal(mesh), mechanical(mesh), material(mesh);
    thermal.distribute_dofs(thermal_fe);
    mechanical.distribute_dofs(mechanical_fe);
    material.distribute_dofs(material_fe);
    dealii::LA::distributed::Vector<double> temperature, displacement;
    temperature.reinit(thermal.locally_owned_dofs(), MPI_COMM_WORLD);
    displacement.reinit(mechanical.locally_owned_dofs(), MPI_COMM_WORLD);
    temperature = 293.15;
    displacement = 0.;
    Kokkos::View<double **, Kokkos::LayoutRight,
                 adamantine::PostProcessor<3>::kokkos_host>
        state("state", 1, 1);
    state(0, 0) = 1.;
    std::unordered_map<dealii::types::global_dof_index, unsigned int> dofs{
        {0, 0}};

    using Tensor = dealii::SymmetricTensor<2, 3>;
    std::vector<std::vector<Tensor>> cases(8, std::vector<Tensor>(1));
    cases[0][0][0][1] = 1.;
    cases[1][0][0][2] = 1.;
    cases[2][0][1][2] = 1.;
    cases[3][0][0][0] = 3.;
    cases[3][0][1][1] = 2.;
    cases[3][0][2][2] = 1.;
    cases[4][0][0][0] = 7.;
    cases[4][0][1][1] = 7.;
    cases[4][0][2][2] = 7.;
    cases[5][0][0][0] = 3.;
    cases[5][0][1][1] = -2.;
    cases[5][0][2][2] = 1.;
    cases[5][0][0][1] = -4.;
    cases[5][0][1][2] = 2.;
    cases[5][0][0][2] = 3.;
    cases[6][0][0][2] = -2.;
    cases[7].resize(2);
    cases[7][0][0][2] = 1.;
    cases[7][1][1][2] = 3.;

    // Both public export paths must execute the shared C++ stress getter.
    for (bool const coupled : {false, true})
    {
      std::string const mode = coupled ? "coupled" : "mechanical";
      std::filesystem::path const destination = output / mode;
      std::filesystem::create_directory(destination);
      boost::property_tree::ptree database;
      database.put("filename_prefix", "witness");
      database.put("output_dir", destination.string() + "/");
      database.put("thermal_output", coupled);
      database.put("mechanical_output", true);
      std::unique_ptr<adamantine::PostProcessor<3>> exporter;
      if (coupled)
        exporter = std::make_unique<adamantine::PostProcessor<3>>(
            MPI_COMM_WORLD, database, thermal, mechanical);
      else
        exporter = std::make_unique<adamantine::PostProcessor<3>>(
            MPI_COMM_WORLD, database, mechanical);
      for (unsigned int i = 0; i < cases.size(); ++i)
      {
        std::vector<std::vector<Tensor>> stress{cases[i]};
        if (coupled)
          exporter->write_output<Kokkos::LayoutRight>(i, double(i), temperature,
                                                      displacement, stress,
                                                      state, dofs, material);
        else
          exporter->write_mechanical_output<Kokkos::LayoutRight>(
              i, double(i), displacement, stress, state, dofs, material);
        if (!std::filesystem::is_regular_file(
                destination / ("witness." + std::to_string(i) + ".0.vtu")))
          throw std::runtime_error(mode + " exporter ignored output_dir");
      }
      exporter->write_pvd();
      if (!std::filesystem::is_regular_file(destination / "witness.pvd"))
        throw std::runtime_error(mode + " PVD missing from output_dir");
    }
    std::cout << "Native exporter regression completed: 16 VTU frames\n";
    return 0;
  }
  catch (std::exception const &error)
  {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
