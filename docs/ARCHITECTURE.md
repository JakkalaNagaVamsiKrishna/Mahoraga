# The Mahoraga Project: Dharma Wheel Orchestrator (Enterprise Scale)

## Objective
Scale "The Auditor" (The Dharma Wheel) into a massive, globally distributed control plane capable of orchestrating model adaptation across 10,000+ edge devices. This architecture transitions the Edge-CV-Hub from a standalone inference engine into a "Fleet-Level Self-Healing AI."

## High-Scale System Topology

To manage massive scale (e.g., autonomous vehicle fleets or city-wide surveillance), the architecture is divided into a three-tier hierarchy: **Edge Devices**, **Regional Aggregators (The Spkes)**, and the **Global Control Plane (The Hub)**.

### Tier 1: The Edge (Fleet Nodes)
*   **Role:** Inference and Uncertainty Calculation.
*   **Action:** Uses the `Edge-CV-Hub` (C++). For every prediction, it calculates an "Uncertainty Score" (e.g., Entropy of the Softmax output).
*   **The "Click":** If the uncertainty is above a threshold, the Edge node takes a snapshot (Raw Image + Latent Embedding) and pushes it.
*   **Scale Tactic:** *Edge-Side Throttling*. To prevent a network DDoS during a sudden environmental shift (e.g., a massive snowstorm), nodes employ a Token Bucket algorithm, limiting OOD uploads to a maximum of 5 per minute per node.

### Tier 2: Regional Aggregators (The Spokes)
*   **Role:** Data Fabric and Initial Filtering.
*   **Action:** **Apache Kafka** clusters deployed in regional edge data centers (e.g., AWS Wavelength). 
*   **Scale Tactic:** *Latent Clustering*. A lightweight Python microservice reads the Kafka stream. It uses fast clustering (e.g., DBSCAN on embeddings) to group similar "failed" images. Instead of forwarding 10,000 images of the *same* new stop sign to the Global Hub, it forwards only 5 representative samples per cluster.

### Tier 3: Global Control Plane (The Hub)
*   **Role:** Active Learning and Orchestration.
*   **Action:** Runs on a centralized **Kubernetes** cluster.
*   **The Adaptation Engine (Kubeflow):**
    1.  **Data Lake (S3):** Ingests the highly-curated, de-duplicated OOD samples from the Regional Aggregators.
    2.  **Teacher Labelling:** A massive, billion-parameter Teacher model (e.g., ViT-Huge) processes the new samples to generate high-confidence pseudo-labels.
    3.  **Continual Distillation:** The `compressor.pipeline` is triggered. It uses a replay buffer (80% historical data, 20% new OOD data) to prevent "Catastrophic Forgetting."
    4.  **Hardware-in-the-Loop (HIL) Testing:** The new model is automatically tested on physical devices (Raspberry Pis / Jetsons) attached to the CI/CD pipeline to guarantee the latency threshold (< 50ms) is still met.

## Deployment & Rollout Strategy

Deploying to 10,000+ devices requires extreme safety mechanisms to prevent a "bad adaptation" from bricking the fleet.

### The "Eight-Handled" Rollout
1.  **Shadow Mode (0% impact):** The new ONNX model is deployed silently alongside the active model. Its predictions are logged but not used by the application.
2.  **Canary Release (1%):** The model is activated on a geographically diverse 1% of the fleet.
3.  **Telemetry Gate:** The Control Plane monitors the Canary nodes for 24 hours. If crash rates or latency spike, an automatic rollback is triggered.
4.  **Phased Rollout (10% -> 50% -> 100%):** Progressive deployment over MQTT, leveraging the C++ `mmap` zero-copy loading for seamless, mid-operation hot-swapping.

## Future Enterprise Applications

1.  **Autonomous Delivery Fleets:** Robots encountering new geographical anomalies (e.g., specific types of construction zones or local wildlife) automatically aggregate that data, adapt, and distribute the "immunity" to the rest of the fleet within 24 hours.
2.  **Global Defect Detection:** Manufacturing plants across the world encountering a new type of material defect. One plant's failure immediately initiates a training cycle that updates the inspection models in all global plants.
3.  **Adversarial Security (The True Mahoraga):** In cybersecurity, if a microservice firewall (running a local ML guard) detects an anomalous traffic pattern that bypasses it, the latent pattern is sent to the Hub. The Hub trains a patch, and the entire global mesh network is updated to recognize and block that specific attack vector before it can spread.