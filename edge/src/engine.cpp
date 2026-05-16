// mahoraga/edge/src/engine.cpp
// ─────────────────────────────────────────────────────────────────────────────
// Mahoraga Advanced Inference Engine
//
// Features:
//   1. Atomic Hot-Swapping of ONNX models via mmap.
//   2. MQTT-based telemetry and control loop.
//   3. Compatible with Edge-CV-Hub model artifacts.
// ─────────────────────────────────────────────────────────────────────────────

#include <iostream>
#include <vector>
#include <string>
#include <memory>
#include <mutex>
#include <chrono>
#include <fstream>

// System headers
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

// Dependencies
#include <onnxruntime_cxx_api.h>
#include <mqtt/async_client.h>
#include "httplib.h"
#include "json.hpp"

using json = nlohmann::json;

// ─── Constants (Compatible with Edge-CV-Hub) ─────────────────────────────────
#ifndef MODEL_PATH
#define MODEL_PATH "model/student_int8.onnx"
#endif

#ifndef SERVER_PORT
#define SERVER_PORT 8080
#endif

#ifndef INPUT_H
#define INPUT_H 224
#endif

#ifndef INPUT_W
#define INPUT_W 224
#endif

#ifndef INPUT_C
#define INPUT_C 3
#endif

const std::string MQTT_SERVER = "tcp://localhost:1883";
const std::string CLIENT_ID = "mahoraga-edge-node-001";
const std::string TOPIC_TELEMETRY = "mahoraga/telemetry/node-001";
const std::string TOPIC_CONTROL = "mahoraga/control/update";

// ─── Model Management ────────────────────────────────────────────────────────

struct ModelInstance {
    void*  mmap_addr = nullptr;
    size_t mmap_size = 0;
    int    fd        = -1;
    std::unique_ptr<Ort::Session> session;
    std::string version;

    ModelInstance(const std::string& path, Ort::Env& env, Ort::SessionOptions& opts) {
        fd = open(path.c_str(), O_RDONLY);
        if (fd < 0) throw std::runtime_error("Cannot open model file");

        struct stat st;
        fstat(fd, &st);
        mmap_size = st.st_size;
        mmap_addr = mmap(nullptr, mmap_size, PROT_READ, MAP_PRIVATE, fd, 0);
        if (mmap_addr == MAP_FAILED) {
            close(fd);
            throw std::runtime_error("mmap failed");
        }

        // Zero-copy loading into ONNX Runtime
        session = std::make_unique<Ort::Session>(env, mmap_addr, mmap_size, opts);
        version = path;
    }

    ~ModelInstance() {
        session.reset();
        if (mmap_addr) munmap(mmap_addr, mmap_size);
        if (fd >= 0) close(fd);
    }
};

// ─── Engine Class ────────────────────────────────────────────────────────────

class MahoragaEngine {
public:
    MahoragaEngine() : env(ORT_LOGGING_LEVEL_WARNING, "Mahoraga"), mqtt_client(MQTT_SERVER, CLIENT_ID) {
        session_options.SetIntraOpNumThreads(1);
        session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        
        // Connect MQTT
        mqtt::connect_options conn_opts;
        conn_opts.set_keep_alive_interval(20);
        conn_opts.set_clean_session(true);
        mqtt_client.connect(conn_opts)->wait();
        mqtt_client.subscribe(TOPIC_CONTROL, 1);
        
        std::cout << "[Mahoraga] MQTT connected and subscribed to control loop." << std::endl;
    }

    void load_initial_model(const std::string& path) {
        active_instance = std::make_shared<ModelInstance>(path, env, session_options);
    }

    void handle_mqtt_update(const std::string& new_model_path) {
        std::lock_guard<std::mutex> lock(swap_mutex);
        std::cout << "[Mahoraga] Turning the Dharma Wheel... Adapting to " << new_model_path << std::endl;
        try {
            auto next = std::make_shared<ModelInstance>(new_model_path, env, session_options);
            active_instance = next;
            std::cout << "[Mahoraga] ADAPTATION COMPLETE." << std::endl;
        } catch (const std::exception& e) {
            std::cerr << "[Mahoraga] Adaptation failed: " << e.what() << std::endl;
        }
    }

    json run_inference(const std::vector<float>& pixels) {
        std::shared_ptr<ModelInstance> current;
        {
            std::lock_guard<std::mutex> lock(swap_mutex);
            current = active_instance;
        }

        // Preprocessing (SIMD Normalization logic would go here)
        // For now, we assume pixels are pre-normalized float32
        
        const char* input_names[] = {"input"};
        const char* output_names[] = {"output"};
        int64_t input_shape[] = {1, INPUT_C, INPUT_H, INPUT_W};

        auto memory_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
            memory_info, const_cast<float*>(pixels.data()), pixels.size(), input_shape, 4
        );

        auto outputs = current->session->Run(Ort::RunOptions{nullptr}, input_names, &input_tensor, 1, output_names, 1);
        float* float_out = outputs.front().GetTensorMutableData<float>();

        // Find max class (Simplified)
        int max_idx = 0;
        float max_val = -1e9;
        for(int i=0; i<10; ++i) { // Assuming 10 classes (CIFAR10)
            if(float_out[i] > max_val) {
                max_val = float_out[i];
                max_idx = i;
            }
        }

        // TELEMETRY: Send embeddings to the Spoke
        // In a real ResNet, we'd pull the latent vector here.
        send_telemetry(max_idx, max_val);

        return {{"class", max_idx}, {"confidence", max_val}, {"version", current->version}};
    }

private:
    void send_telemetry(int cls, float conf) {
        json msg;
        msg["device_id"] = CLIENT_ID;
        msg["timestamp"] = "2026-05-16T18:00:00Z"; // Mock timestamp
        msg["model_version"] = active_instance->version;
        msg["inference"] = {{"prediction", std::to_string(cls)}, {"confidence", conf}};
        msg["data"] = {{"embedding", {0.1, 0.2, 0.3}}}; // Mock embedding for now

        mqtt_client.publish(TOPIC_TELEMETRY, msg.dump(), 0, false);
    }

    Ort::Env env;
    Ort::SessionOptions session_options;
    std::shared_ptr<ModelInstance> active_instance;
    std::mutex swap_mutex;
    mqtt::async_client mqtt_client;
};

// ─── Main Server ─────────────────────────────────────────────────────────────

int main() {
    MahoragaEngine engine;
    try {
        engine.load_initial_model(MODEL_PATH);
    } catch(...) {
        std::cerr << "Warning: Could not load initial model at " << MODEL_PATH << std::endl;
    }

    httplib::Server svr;

    svr.Post("/predict", [&](const httplib::Request& req, httplib::Response& res) {
        // Assume binary float32 payload for speed
        std::vector<float> pixels(INPUT_C * INPUT_H * INPUT_W);
        std::memcpy(pixels.data(), req.body.data(), pixels.size() * sizeof(float));

        auto result = engine.run_inference(pixels);
        res.set_content(result.dump(), "application/json");
    });

    std::cout << "[Mahoraga] Edge Server listening on port " << SERVER_PORT << std::endl;
    svr.listen("0.0.0.0", SERVER_PORT);

    return 0;
}
