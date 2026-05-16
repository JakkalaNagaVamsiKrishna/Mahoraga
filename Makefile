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
	@echo "  make hub          Run global control plane (placeholder)"
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

test:
	pytest tests/
