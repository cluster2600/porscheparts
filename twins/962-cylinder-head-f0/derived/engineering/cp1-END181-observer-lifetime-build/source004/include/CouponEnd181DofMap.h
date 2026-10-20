// Held source for the RICH2 END181 observability study. Not built or executed.
#pragma once

#include "Output.h"

#include <array>
#include <cstdint>
#include <string>
#include <vector>

/** Fixed-case, read-only integer map. No residual or Jacobian is evaluated. */
class CouponEnd181DofMap : public Output
{
public:
  static InputParameters validParams();
  explicit CouponEnd181DofMap(const InputParameters & parameters);
  std::string filename();

  struct Row
  {
    std::uint64_t node_id;
    unsigned int variable_slot;
    bool dof_present;
    std::uint64_t global_dof;
    std::array<std::string, 3> coordinate_words;
    bool constrained;
  };

  // These same production checks are the targets of the held synthetic guards.
  static bool originalConstraint(std::uint64_t node_id, unsigned int variable_slot);
  static std::string binary64LEWord(Real value);
  static std::string validateRows(const std::vector<Row> & rows,
                                  const std::array<unsigned int, 4> & variable_numbers,
                                  std::uint64_t ndof);

protected:
  void output() override;

private:
  std::string _file_base;
  bool _written = false;
};
