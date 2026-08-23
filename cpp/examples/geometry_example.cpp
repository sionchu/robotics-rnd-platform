#include <iostream>

#include "robotics_rnd/geometry/vector3.hpp"

int main() {
  const robotics_rnd::geometry::Vector3 translation_m{0.3, 0.4, 0.0};
  std::cout << "translation norm (m): " << translation_m.norm_m() << '\n';
  return 0;
}
