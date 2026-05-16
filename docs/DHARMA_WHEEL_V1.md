# The Mahoraga Project: Dharma Wheel Orchestrator

## Objective
Design and implement "The Auditor" (The Dharma Wheel) to transform the static `Edge-CV-Hub` into a self-adapting, continuous-learning system. The orchestrator will monitor edge devices for Out-of-Distribution (OOD) data, aggregate this data via MQTT, and automatically orchestrate re-distillation pipelines on Kubernetes using Kubeflow.

## Architectural Blueprint

Based on the selected tech stack, the architecture is divided into four main lifecycle stages:

### 1. The Divergent Sila: Edge-Side Emission
*   **Action:** The C++ inference server (Edge-CV-Hub) is modified to output not just the final prediction, but also the **Latent Embeddings** (the intermediate feature vectors from the penultimate layer).
*   **Protocol:** Embeddings and their corresponding raw images (if sampled) are published to an **MQTT Broker** (e.g., Mosquitto).
*   **Rationale:** MQTT is lightweight and handles the intermittent connectivity typical of edge devices perfectly.

### 2. The Wheel Click: Cloud-Side Drift Detection (OOD)
*   **Action:** A dedicated Cloud Microservice subscribes to the MQTT topics. It analyzes the incoming latent embeddings against the "known" data manifold (using algorithms like Isolation Forests, Mahalanobis Distance, or GMMs).
*   **Trigger:** When the distance exceeds a certain threshold (Drift Detected), the "Wheel Clicks". The system flags the corresponding raw images as "High Value" and stores them in a Cloud Data Lake (e.g., S3/MinIO).

### 3. The Adaptation: Automated Re-Distillation (Kubeflow)
*   **Action:** Once enough "High Value" samples are aggregated (e.g., 5,000 new OOD images), the orchestrator triggers a **Kubeflow Pipeline**.
*   **Pipeline Steps:**
    1.  **Teacher Labelling:** The heavy Teacher model (e.g., ResNet50/ViT) predicts pseudo-labels for the new data.
    2.  **Distillation:** The `compressor.pipeline` runs, fine-tuning the Student model on the combined dataset (Historical Data + New OOD Data).
    3.  **Validation:** The new model passes through the existing `benchmark.runner` gates.

### 4. The Resolution: Over-The-Air (OTA) Updates
*   **Action:** If the new model passes the gates, the Kubeflow pipeline publishes the new INT8 ONNX artifact to a Model Registry.
*   **Deployment:** Edge devices poll the registry or receive an MQTT command to pull the new model. The `mmap` architecture of Edge-CV-Hub allows for near-instant "Hot-Swapping" with zero downtime.

## Implementation Steps

1.  **Phase 1: MQTT & Latent Extraction**
    *   Update `Edge-CV-Hub` C++ code to extract embeddings.
    *   Set up Mosquitto broker and implement an MQTT publisher in C++.
2.  **Phase 2: Drift Detection Engine**
    *   Build a Python service using `scikit-learn` or `PyOD` to process embeddings from MQTT and detect OOD samples.
3.  **Phase 3: Kubeflow Integration**
    *   Containerize the existing `compressor` and `benchmark` modules.
    *   Define a Kubeflow `Pipeline` (DAG) that connects Data Fetching -> Teacher Labelling -> Distillation -> Export.
4.  **Phase 4: OTA & Control Loop**
    *   Implement versioning and a polling/push mechanism for the Edge devices to download the updated `.onnx` files.

## Migration & Rollback Strategy
*   **Shadow Mode:** New models are initially deployed in "Shadow Mode" on a subset of edge devices to monitor stability.
*   **Instant Rollback:** Edge devices retain the `N-1` ONNX file. If latency spikes or the system crashes, it instantly falls back to the previous memory-mapped model.