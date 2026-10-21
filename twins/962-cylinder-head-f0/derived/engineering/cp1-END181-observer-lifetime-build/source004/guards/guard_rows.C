// HELD/UNRUN. Synthetic metadata only; requires a separately admitted matching SDK/build.
// Link the production observer implementation; no MOOSE app is instantiated here.
#include "CouponEnd181DofMap.h"

#include <array>
#include <limits>
#include <stdexcept>
#include <vector>

namespace
{
void require(bool condition, const char * message)
{
  if (!condition)
    throw std::runtime_error(message);
}
}

int main()
{
  using Observer = CouponEnd181DofMap;
  std::vector<Observer::Row> synthetic;
  for (std::uint64_t node = 0; node < 425; ++node)
    for (unsigned int slot = 0; slot < 4; ++slot)
      synthetic.push_back({node,
                           slot,
                           slot < 3,
                           slot < 3 ? ((node * 3 + slot) * 7) % 1275 : 0,
                           {Observer::binary64LEWord(static_cast<Real>(node)),
                            Observer::binary64LEWord(0), Observer::binary64LEWord(0)},
                           Observer::originalConstraint(node, slot)});
  // This permutation deliberately breaks any sorted-node -> sorted-DOF shortcut.
  const std::array<unsigned int, 4> variable_numbers = {2, 0, 3, 1};
  const auto valid = [&variable_numbers](const std::vector<Observer::Row> & rows,
                                       std::uint64_t ndof = 1275)
  { return Observer::validateRows(rows, variable_numbers, ndof).empty(); };
  require(valid(synthetic), "Complete permuted synthetic map refused.");
  auto with_placeholder = synthetic;
  with_placeholder[3].dof_present = true;
  with_placeholder[3].global_dof = 1275;
  require(valid(with_placeholder, 1276), "Nonphysical placeholder presence was hidden/refused.");
  auto changed = synthetic;
  changed.pop_back();
  require(!valid(changed), "Missing row accepted.");
  changed = synthetic;
  changed[4] = changed[0];
  require(!valid(changed), "Duplicate source-node/variable pair accepted.");
  changed = synthetic;
  changed[4].global_dof = changed[0].global_dof;
  require(!valid(changed), "Duplicate global DOF accepted.");
  changed = synthetic;
  changed[0].dof_present = false;
  require(!valid(changed), "Missing physical displacement DOF accepted.");
  changed = synthetic;
  changed[0].constrained = false;
  require(!valid(changed), "Changed original mask accepted.");
  changed = synthetic;
  changed[0].node_id = 425;
  require(!valid(changed), "Out-of-range source node accepted.");
  changed = synthetic;
  changed[0].global_dof = 1275;
  require(!valid(changed), "Out-of-range global DOF accepted.");
  changed = synthetic;
  changed[1].coordinate_words[0] = Observer::binary64LEWord(1);
  require(!valid(changed), "Inconsistent coordinate words accepted.");
  changed = synthetic;
  changed[0].coordinate_words[0] = "000";
  require(!valid(changed), "Truncated coordinate word accepted.");
  changed = synthetic;
  changed[3].global_dof = 1;
  require(!valid(changed), "Absent placeholder fabricated index accepted.");
  require(!Observer::validateRows(synthetic, {2, 0, 3, 2}, 1275).empty(),
          "Duplicate variable number accepted.");
  require(!valid(synthetic, 1276), "Unaccounted global DOF accepted.");
  require(Observer::binary64LEWord(Real(0)) == "0000000000000000", "Zero word changed.");
  require(Observer::binary64LEWord(Real(-0.0)) == "0000000000000080", "Signed zero lost.");
  require(Observer::binary64LEWord(Real(1)) == "000000000000f03f", "Unit word changed.");
  bool refused_nonfinite = false;
  try
  {
    Observer::binary64LEWord(std::numeric_limits<Real>::quiet_NaN());
  }
  catch (const std::invalid_argument &)
  {
    refused_nonfinite = true;
  }
  require(refused_nonfinite, "Nonfinite metadata accepted.");
  return 0;
}
