cmake_minimum_required(VERSION 3.20)
project(robotics_rnd_cpp VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(robotics_rnd_geometry INTERFACE)
target_include_directories(robotics_rnd_geometry INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(geometry_example examples/geometry_example.cpp)
target_link_libraries(geometry_example PRIVATE robotics_rnd_geometry)

enable_testing()
add_executable(geometry_smoke tests/geometry_smoke.cpp)
target_link_libraries(geometry_smoke PRIVATE robotics_rnd_geometry)
add_test(NAME geometry_smoke COMMAND geometry_smoke)
