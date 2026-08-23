#include <cassert>
#include <cmath>
#include <stdexcept>

#include "robotics_rnd/geometry/vector3.hpp"

int main() {
  const robotics_rnd::geometry::Vector3 vector{0.3, 0.4, 0.0};
  assert(std::abs(vector.norm_m() - 0.5) < 1e-12);

  bool rejected = false;
  try {
    const robotics_rnd::geometry::Vector3 invalid{NAN, 0.0, 0.0};
    static_cast<void>(invalid);
  } catch (const std::invalid_argument&) {
    rejected = true;
  }
  assert(rejected);
  return 0;
}
