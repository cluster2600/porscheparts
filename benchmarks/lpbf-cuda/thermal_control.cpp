// Synthetic CPU controls for the pinned upstream thermal implementation.
#include <cassert>
#include <cmath>
#include "thermal.hpp"
#include "constants.hpp"

int main() {
    double xyz[] = {0., 0., 0., 1.9e-5, 0., 0.};
    double radii[] = {1e-5, 1e-5};
    double areas[] = {M_PI * 1e-10, M_PI * 1e-10};
    double temperatures[] = {ENVIORNMENT_T, ENVIORNMENT_T};
    particles_t particles{};
    particles.n_particles = 2;
    particles.xyzs = xyz;
    particles.rs = radii;
    particles.areas = areas;
    particles.Ts = temperatures;
    assert(computeConvection(&particles, 0) == 0.);
    assert(computeRadiation(&particles, 0) == 0.);
    assert(computeConduction(&particles, 0, 1) == 0.);
    assert(computeCapacity(ENVIORNMENT_T) == C_SOLID);
    temperatures[0] += 100.;
    const double forward = computeConduction(&particles, 0, 1);
    const double reverse = computeConduction(&particles, 1, 0);
    assert(std::isfinite(forward) && forward > 0.);
    assert(std::abs(forward + reverse) < 1e-12);
    assert(computeConvection(&particles, 0) > 0.);
    assert(computeRadiation(&particles, 0) > 0.);
    xyz[3] = 3e-5;
    assert(computeConduction(&particles, 0, 1) == 0.);
    assert(computeCapacity(MELTING_T) > C_SOLID);
    return 0;
}
