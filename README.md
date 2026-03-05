# AIoT Platform - K8s Cluster Backup

Full Kubernetes cluster backup for the AIoT monitoring platform.

## Architecture
```
Sensors > EMQX (MQTT) > Kafka Bridge > Redpanda > Qdrant Indexer > Qdrant
User (WebUI) > API Gateway (Cerebrus) > Cerebras LLM (llama3.1-8b) + Digital Twin + Qdrant
```

## Components
**aiot:** api-gateway, digital-twin, qdrant, qdrant-indexer, rag-worker, redpanda(4x), postgres, redis, mirror-maker2, pgadmin
**emqx:** emqx (MQTT broker), mqtt-kafka-bridge
**default:** open-webui, grafana, prometheus, elasticsearch, kibana, ws-proxy

## Structure
```
src/     - Python source code
config/  - Configuration files
k8s/     - Kubernetes manifests
```

## LLM
Provider: Cerebras | Model: llama3.1-8b | Secret: cerebras-api-key

## Restore
```bash
kubectl create namespace aiot && kubectl create namespace emqx
kubectl apply -f k8s/aiot/cm-*.yaml && kubectl apply -f k8s/emqx/cm-*.yaml
kubectl create secret generic cerebras-api-key -n aiot --from-literal=key=YOUR_KEY
kubectl apply -f k8s/aiot/ss-*.yaml && kubectl apply -f k8s/emqx/ss-*.yaml
kubectl apply -f k8s/aiot/deploy-*.yaml && kubectl apply -f k8s/emqx/deploy-*.yaml
kubectl apply -f k8s/aiot/services.yaml && kubectl apply -f k8s/emqx/services.yaml
```
