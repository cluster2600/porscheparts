// Held source for the RICH2 END181 observability study. Not built or executed.
#include "CouponEnd181DofMap.h"

#include "FEProblem.h"
#include "MooseMesh.h"
#include "MooseVariableFieldBase.h"
#include "NonlinearSystemBase.h"
#include "libmesh/fe_type.h"
#include "libmesh/libmesh.h"
#include "libmesh/transient_system.h"
#include "petscsys.h"
#include "petscversion.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <utility>

registerMooseObject("CouponEnd181ObserverApp", CouponEnd181DofMap);

InputParameters
CouponEnd181DofMap::validParams()
{
  InputParameters params = Output::validParams();
  params.addClassDescription("Observe the fixed RICH2 END181 node/global-DOF association only.");
  params.addRequiredParam<FileName>("file_base", "Fresh owned integer-map output file base.");
  params.set<ExecFlagEnum>("execute_on", true) = EXEC_TIMESTEP_END;
  params.set<int>("start_step") = 181;
  params.set<int>("end_step") = 181;
  params.set<bool>("use_displaced") = false;
  return params;
}

CouponEnd181DofMap::CouponEnd181DofMap(const InputParameters & parameters)
  : Output(parameters), _file_base(getParam<FileName>("file_base"))
{
}

std::string
CouponEnd181DofMap::filename()
{
  return _file_base + ".json";
}

bool
CouponEnd181DofMap::originalConstraint(std::uint64_t node_id, unsigned int slot)
{
  return (node_id == 0 && slot < 3) || (node_id == 32 && (slot == 1 || slot == 2)) ||
         (node_id == 137 && slot == 2);
}

std::string
CouponEnd181DofMap::binary64LEWord(Real value)
{
  static_assert(sizeof(Real) == 8 && std::numeric_limits<Real>::is_iec559 &&
                    std::numeric_limits<Real>::digits == 53,
                "The observation requires IEEE binary64 Real.");
  if (!std::isfinite(value))
    throw std::invalid_argument("Nonfinite observation metadata.");
  std::uint64_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  std::ostringstream word;
  word << std::hex << std::setfill('0');
  for (unsigned int byte = 0; byte < 8; ++byte)
    word << std::setw(2) << ((bits >> (8 * byte)) & 0xffu);
  return word.str();
}

std::string
CouponEnd181DofMap::validateRows(const std::vector<Row> & rows,
                               const std::array<unsigned int, 4> & variable_numbers,
                               std::uint64_t ndof)
{
  if (rows.size() != 1700 || ndof < 1275 || ndof > 1700)
    return "Incomplete fixed-case row or global-DOF census.";
  if (std::set<unsigned int>(variable_numbers.begin(), variable_numbers.end()) !=
      std::set<unsigned int>{0, 1, 2, 3})
    return "Variable numbers are not the complete four-variable permutation.";
  std::set<std::pair<std::uint64_t, unsigned int>> pairs;
  std::set<std::uint64_t> global_dofs;
  std::map<std::uint64_t, std::array<std::string, 3>> coordinates;
  unsigned int constrained_count = 0;
  for (const auto & row : rows)
  {
    if (row.node_id >= 425 || row.variable_slot >= 4 ||
        !pairs.emplace(row.node_id, row.variable_slot).second)
      return "Missing, duplicate or out-of-range source node/variable association.";
    for (const auto & word : row.coordinate_words)
      if (word.size() != 16 || word.find_first_not_of("0123456789abcdef") != std::string::npos)
        return "Coordinate metadata is not a binary64 LE hexadecimal word.";
    const auto inserted = coordinates.emplace(row.node_id, row.coordinate_words);
    if (!inserted.second && inserted.first->second != row.coordinate_words)
      return "Coordinate words disagree between variables at one source node.";
    if (row.variable_slot < 3 && !row.dof_present)
      return "A physical displacement DOF is absent at END181.";
    if (row.constrained != originalConstraint(row.node_id, row.variable_slot))
      return "The original six-component constraint mask changed.";
    constrained_count += row.constrained;
    if (row.dof_present)
    {
      if (row.global_dof >= ndof || !global_dofs.insert(row.global_dof).second)
        return "Duplicate or out-of-range global DOF.";
    }
    else if (row.global_dof != 0)
      return "An absent placeholder row carries a fabricated index.";
  }
  // The pair range/cardinality proves all425*4 pairs; the bounded unique index
  // range/cardinality proves every global DOF, without assuming node ordering.
  if (pairs.size() != 1700 || coordinates.size() != 425 ||
      global_dofs.size() != ndof || constrained_count != 6)
    return "Incomplete node, global-DOF or original-mask closure.";
  return "";
}

void
CouponEnd181DofMap::output()
{
  if (_written || !_transient || _use_displaced || _t_step != 181 ||
      _current_execute_flag != EXEC_TIMESTEP_END || comm().size() != 1 ||
      libMesh::n_threads() != 1 || _problem_ptr->mesh().isDistributedMesh())
    mooseError("CouponEnd181DofMap requires one undisplaced, one-thread, serial END181 observation.");
#if defined(PETSC_USE_COMPLEX)
  mooseError("The passive vector contract requires real binary64 PETSc scalars.");
#endif
  if (sizeof(PetscScalar) != 8 || std::numeric_limits<PetscReal>::digits != 53 ||
      (sizeof(PetscInt) != 4 && sizeof(PetscInt) != 8))
    mooseError("The passive vector scalar/index ABI is outside the held contract.");

  auto & nl = _problem_ptr->getNonlinearSystemBase(0);
  const auto & sys = nl.system();
  if (sys.name() != "nl0" || sys.n_vars() != 4)
    mooseError("The fixed nl0/four-variable observation contract changed.");
  const std::array<std::string, 4> names = {
      "disp_x", "disp_y", "disp_z", "inactive_placeholder"};
  std::array<unsigned int, 4> numbers;
  std::array<std::string, 4> scaling_words;
  for (unsigned int slot = 0; slot < names.size(); ++slot)
  {
    const auto & variable = nl.getVariable(0, names[slot]);
    numbers[slot] = variable.number();
    if (variable.isArray() || variable.count() != 1 || !variable.isNodal() ||
        variable.feType().family != libMesh::LAGRANGE ||
        variable.feType().order != libMesh::FIRST || numbers[slot] >= sys.n_vars() ||
        sys.variable_name(numbers[slot]) != names[slot])
      mooseError("The observed variable is not the original scalar FIRST/LAGRANGE variable.");
    scaling_words[slot] = binary64LEWord(variable.scalingFactor());
  }

  std::vector<Row> rows;
  auto & mesh = _problem_ptr->mesh();
  for (const auto & node : as_range(mesh.localNodesBegin(), mesh.localNodesEnd()))
  {
    const std::array<std::string, 3> words = {
        binary64LEWord((*node)(0)), binary64LEWord((*node)(1)), binary64LEWord((*node)(2))};
    for (unsigned int slot = 0; slot < names.size(); ++slot)
    {
      const auto count = node->n_dofs(sys.number(), numbers[slot]);
      if (count > 1)
        mooseError("More than one nodal DOF is outside the fixed observation contract.");
      const auto dof = count ? node->dof_number(sys.number(), numbers[slot], 0) : 0;
      rows.push_back({node->id(), slot, count == 1, dof, words,
                      originalConstraint(node->id(), slot)});
    }
  }
  const auto refusal = validateRows(rows, numbers, sys.n_dofs());
  if (!refusal.empty())
    mooseError("CouponEnd181DofMap refused association: ", refusal);
  std::sort(rows.begin(), rows.end(), [](const Row & a, const Row & b)
            { return std::make_pair(a.node_id, a.variable_slot) <
                     std::make_pair(b.node_id, b.variable_slot); });

  std::ostringstream data;
  data << "{\"schema\":\"962-RICH2-END181-node-global-DOF-map/v1\","
       << "\"scope\":\"integer_associations_only_no_field_acceptance\","
       << "\"constraint_mask_scope\":\"original_case_expected_labels_not_live_BC_or_DofMap_observation\","
       << "\"step\":" << _t_step << ",\"event\":\"TIMESTEP_END\","
       << "\"time_binary64_LE_hex\":\"" << binary64LEWord(_time) << "\","
       << "\"dt_binary64_LE_hex\":\"" << binary64LEWord(_dt) << "\","
       << "\"nonlinear_system_name\":\"nl0\",\"nonlinear_system_number\":" << sys.number()
       << ",\"global_DOF_count\":" << sys.n_dofs()
       << ",\"physical_displacement_DOF_count\":1275,\"source_node_count\":425,"
       << "\"MPI_ranks\":1,\"threads\":1,\"Real_bytes\":" << sizeof(Real)
       << ",\"PetscScalar_bytes\":" << sizeof(PetscScalar)
       << ",\"PetscInt_bytes\":" << sizeof(PetscInt)
       << ",\"PETSc_version\":[" << PETSC_VERSION_MAJOR << ',' << PETSC_VERSION_MINOR << ','
       << PETSC_VERSION_SUBMINOR << "],\"variables\":[";
  for (unsigned int slot = 0; slot < names.size(); ++slot)
  {
    if (slot)
      data << ',';
    data << "{\"slot\":" << slot << ",\"name\":\"" << names[slot]
         << "\",\"number\":" << numbers[slot]
         << ",\"family\":\"LAGRANGE\",\"order\":\"FIRST\",\"physical_displacement\":"
         << (slot < 3 ? "true" : "false") << ",\"existing_scaling_binary64_LE_hex\":\""
         << scaling_words[slot] << "\"}";
  }
  data << "],\"rows\":[";
  for (unsigned int i = 0; i < rows.size(); ++i)
  {
    const auto & row = rows[i];
    if (i)
      data << ',';
    data << "{\"source_node_ID\":" << row.node_id << ",\"variable_slot\":" << row.variable_slot
         << ",\"variable_number\":" << numbers[row.variable_slot]
         << ",\"dof_present\":" << (row.dof_present ? "true" : "false")
         << ",\"DOF_state\":\"" << (row.dof_present ? "present" : "absent") << "\""
         << ",\"global_DOF\":";
    if (row.dof_present)
      data << row.global_dof;
    else
      data << "null";
    data << ",\"coordinate_binary64_LE_hex\":[\"" << row.coordinate_words[0] << "\",\""
         << row.coordinate_words[1] << "\",\"" << row.coordinate_words[2]
         << "\"],\"constrained\":" << (row.constrained ? "true" : "false") << '}';
  }
  data << "],\"reaction_convention\":{\"system\":\"auxiliary_save_in\","
       << "\"save_in\":[\"rx\",\"ry\",\"rz\"],\"DOF_presence_is_not_kernel_activation\":true,"
       << "\"reaction_values_recorded_by_this_observer\":false,"
       << "\"unchanged_END181_collector_required\":true,"
       << "\"solver_F_has_nodal_BC_rows\":true,\"constrained_F_is_not_reaction\":true,"
       << "\"scaling_changed_or_removed\":false},\"assembly_invoked\":false,"
       << "\"solution_or_physical_state_written\":false,\"field_acceptance\":false}\n";
  const auto contents = data.str();
  if (contents.size() > 1024 * 1024)
    mooseError("The fixed integer-map output exceeds its 1MiB sub-budget.");
  const auto path = filename();
  const auto pending = path + ".part";
  if (std::filesystem::exists(path) || std::filesystem::exists(pending))
    mooseError("The integer-map output must be fresh and must never overwrite an earlier map.");
  std::ofstream out(pending, std::ios::binary | std::ios::out | std::ios::trunc);
  out << contents;
  out.close();
  if (!out)
    mooseError("Could not complete the fixed integer-map output; retain the partial file.");
  std::filesystem::rename(pending, path);
  _written = true;
}
