#include "setup.hpp"
#include <cmath>
#include <cstdlib>
#include <iostream>

// Periodic fluid at rest: analytic density 1 and velocity 0 after 16 steps.
// This is independent of the historical head geometry and thermal study.
void main_setup() {
    LBM lbm(16u, 16u, 16u, 0.1f, 0.0f, 0.0f, 0.0f, 0.0f, 0.1f, 0.0f);
    lbm.run(16u);
    lbm.update_fields();
    lbm.rho.read_from_device();
    lbm.u.read_from_device();
    for (ulong n = 0; n < lbm.get_N(); ++n) {
        if (!std::isfinite(lbm.rho[n]) || std::fabs(lbm.rho[n] - 1.0f) > 1e-5f
            || !std::isfinite(lbm.u.x[n]) || std::fabs(lbm.u.x[n]) > 1e-6f
            || !std::isfinite(lbm.u.y[n]) || std::fabs(lbm.u.y[n]) > 1e-6f
            || !std::isfinite(lbm.u.z[n]) || std::fabs(lbm.u.z[n]) > 1e-6f) {
            std::cerr << "Periodic rest-state check failed at cell " << n << '\n';
            std::exit(1);
        }
    }
    std::cout << "FLUIDX3D_PERIODIC_REST_CPU_PASS\n";
}
