#pragma once

#include <cmath>
#include <stdexcept>

namespace robotics_rnd::geometry {

struct Vector3 {
  double x_m{};
  double y_m{};
  double z_m{};

  Vector3(double x, double y, double z) : x_m{x}, y_m{y}, z_m{z} {
    if (!std::isfinite(x_m) || !std::isfinite(y_m) || !std::isfinite(z_m)) {
      throw std::invalid_argument{"Vector3 meter values must be finite"};
    }
  }

  [[nodiscard]] double norm_m() const noexcept {
    return std::sqrt(x_m * x_m + y_m * y_m + z_m * z_m);
  }
};

}  // namespace robotics_rnd::geometry
