cmake_minimum_required(VERSION 3.20)
project(mahoraga_edge CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_CXX_FLAGS_RELEASE "-O3 -ffast-math")

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# ── Config (Mirroring Edge-CV-Hub for compatibility) ─────────────────────────
set(MODEL_PATH  "model/student_int8.onnx" CACHE STRING "Path to ONNX model")
set(SERVER_PORT "8080"                    CACHE STRING "HTTP server port")
set(INPUT_H     "224"                     CACHE STRING "Input image height")
set(INPUT_W     "224"                     CACHE STRING "Input image width")
set(INPUT_C     "3"                       CACHE STRING "Input channels")

add_definitions(
  -DMODEL_PATH="${MODEL_PATH}"
  -DSERVER_PORT=${SERVER_PORT}
  -DINPUT_H=${INPUT_H}
  -DINPUT_W=${INPUT_W}
  -DINPUT_C=${INPUT_C}
)

# ── Dependencies ──────────────────────────────────────────────────────────────

# 1. ONNX Runtime
if(NOT DEFINED ONNXRUNTIME_ROOT)
  set(ONNXRUNTIME_ROOT "/opt/onnxruntime")
endif()

find_path(ORT_INCLUDE_DIR
  NAMES onnxruntime_cxx_api.h
  HINTS ${ONNXRUNTIME_ROOT}/include
)

find_library(ORT_LIB
  NAMES onnxruntime
  HINTS ${ONNXRUNTIME_ROOT}/lib
)

# 2. Paho MQTT C++
find_package(PahoMqttCpp REQUIRED)

# ── Executable ────────────────────────────────────────────────────────────────
add_executable(mahoraga_edge
  src/engine.cpp
)

target_include_directories(mahoraga_edge PRIVATE
  ${ORT_INCLUDE_DIR}
  ${CMAKE_SOURCE_DIR}/include       # For httplib.h and json.hpp (vendored from previous project)
)

target_link_libraries(mahoraga_edge PRIVATE
  ${ORT_LIB}
  PahoMqttCpp::paho-mqttpp3
  pthread
)
