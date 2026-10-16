#include <research_build_profile.hh>

#include <iostream>
#include <stdexcept>
#include <tuple>
#include <vector>

int main()
{
  adamantine::require_research_build_profile(3, 1, 0, "polynomial", "host", false);
  using Case = std::tuple<int, int, int, std::string, std::string, bool>;
  std::vector<Case> const unsupported{
      {2, 1, 0, "polynomial", "host", false},
      {3, 2, 0, "polynomial", "host", false},
      {3, 1, 1, "polynomial", "host", false},
      {3, 1, 0, "table", "host", false},
      {3, 1, 0, "polynomial", "device", false},
      {3, 1, 0, "polynomial", "host", true}};
  for (auto const &test : unsupported)
  {
    bool rejected = false;
    try
    {
      std::apply(adamantine::require_research_build_profile, test);
    }
    catch (std::invalid_argument const &error)
    {
      rejected = std::string(error.what()).find("Unsupported research build profile") !=
                 std::string::npos;
    }
    if (!rejected)
      throw std::runtime_error("unsupported profile was not rejected");
  }
  std::cout << "Profile guard passed: supported profile and six rejection cases\n";
}
