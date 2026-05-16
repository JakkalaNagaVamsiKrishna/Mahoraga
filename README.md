# Mahoraga: Self-Adaptive ML Orchestration

**Mahoraga** is an enterprise-scale control plane designed to manage, monitor, and evolve distributed Machine Learning models across thousands of edge devices. 

Building upon the foundation of the [Edge-CV-Hub](https://github.com/JakkalaNagaVamsiKrishna/edge-inference-project), Mahoraga implements the "Dharma Wheel" orchestrator—a system that detects model drift in the field and automatically triggers cloud-side re-distillation to keep the fleet updated and resilient.

## 📂 Project Structure

```text
mahoraga/
├── api/            # Shared schemas and Pydantic models
├── edge/           # Edge integration & Mock client
├── spoke/          # Regional Aggregators (MQTT -> Kafka)
│   ├── clustering/ # DBSCAN latent clustering logic
│   └── gateway/    # Messaging bridge
├── hub/            # Global Control Plane (Kubeflow)
├── infra/          # Docker & Kubernetes configuration
├── shared/         # Common utilities
├── Makefile        # Project management commands
└── requirements.txt
```

## 🚀 Quick Start

1. **Install Dependencies:**
   ```bash
   make setup
   ```

2. **Start Infrastructure:**
   ```bash
   make infra-up
   ```

3. **Run Spoke Gateway:**
   ```bash
   make spoke
   ```

4. **Run OTA Orchestrator:**
   ```bash
   make ota
   ```

---
*Status: Architecture Fully Implemented (v1.0.0)*
