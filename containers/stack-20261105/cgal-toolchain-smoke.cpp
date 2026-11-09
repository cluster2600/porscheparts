#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/squared_distance_3.h>
#include <CGAL/version.h>
#include <iostream>
#include <string>
int main() {
    using K = CGAL::Exact_predicates_inexact_constructions_kernel;
    const K::Point_3 a(0, 0, 0), b(3, 4, 0);
    if (CGAL::squared_distance(a, b) != 25 || std::string(CGAL_VERSION_STR) != "6.2.1")
        return 1;
    std::cout << "CGAL 6.2.1 synthetic distance check passed\n";
}
