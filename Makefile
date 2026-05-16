.PHONY: setup infra-up infra-down mock-edge spoke hub test help

help:
	@echo "Mahoraga: Self-Adaptive ML Orchestration"
	@echo "────────────────────────────────────────"
	@echo "Usage:"
	@echo "  make setup        Install Python dependencies"
	@echo "  make infra-up     Start MQTT & Kafka via Docker"
	@echo "  make infra-down   Stop Infrastructure"
	@echo "  make mock-edge    Run simulated edge client"
	@echo "  make spoke        Run regional aggregator gateway"
	@echo "  make cluster      Run latent clustering processor"
	@echo "  make hub          Run global sample collector"
	@echo "  make ota          Run OTA rollout orchestrator"
	@echo "  make test         Run all tests"

setup:
	pip install -r requirements.txt

infra-up:
	docker compose -f infra/docker/docker-compose.yml up -d

infra-down:
	docker compose -f infra/docker/docker-compose.yml down

mock-edge:
	python -m edge.src.mock_client

spoke:
	python -m spoke.src.gateway.main

cluster:
	python -m spoke.src.clustering.processor

hub:
	python -m hub.services.collector

ota:
	python -m hub.services.ota_orchestrator

test:
	pytest tests/
