# AIoT Platform - K8s Cluster Backup

Complete Kubernetes cluster backup for the AIoT industrial monitoring platform.

**Last updated:** 2026-03-10

## Architecture

```
Sensors (simulator) -> EMQX (MQTT) -> mqtt-kafka-bridge -> Redpanda (Kafka)
                                                              |
                                                    qdrant-indexer -> Qdrant (vectors)
                                                    pg-sink -> PostgreSQL (history)
                                                    redis-pg-flusher -> Redis -> PostgreSQL

User (Open WebUI) -> API Gateway (Cerebrus) -> RAG Worker v9
                                                 |-- Simple query -> Bank (Redis db=5) -> 0 tokens
                                                 |-- Repeat query -> Cache (Redis db=3) -> 0 tokens
                                                 |-- Junk query   -> Blocked            -> 0 tokens
                                                 +-- Complex query -> Cerebras LLM      -> ~500 tokens

Ngrok tunnel -> RAG Worker (same pipeline)
```

## Components

### Namespace: aiot

| Component | Type | Description |
|-----------|------|-------------|
| sensor-simulator | Deployment | Generates IoT sensor data (418 machines) |
| redis-master | Deployment | Central cache + real-time data store |
| qdrant | Deployment | Vector database for RAG |
| qdrant-indexer | Deployment | Indexes sensor data into Qdrant |
| pg-sink | Deployment | Writes sensor data to PostgreSQL |
| redis-pg-flusher | Deployment | Flushes Redis data to PostgreSQL |
| postgres | StatefulSet | PostgreSQL with partitioned tables |
| redpanda | StatefulSet | Kafka-compatible message broker |
| digital-twin | Deployment | Digital twin engine |
| api-gateway | Deployment | Cerebrus API gateway |
| rag-worker | Deployment | RAG Worker v9 (bank/cache/LLM routing) |
| ngrok-proxy | Deployment | Proxy for ngrok tunnel |
| pgadmin | Deployment | PostgreSQL admin UI |
| pg-partition-mgr | CronJob | Auto-creates monthly partitions |

### Namespace: emqx

| Component | Type | Description |
|-----------|------|-------------|
| emqx | StatefulSet | MQTT broker |
| mqtt-kafka-bridge | Deployment | MQTT to Kafka bridge |

### Namespace: default

| Component | Type | Description |
|-----------|------|-------------|
| elasticsearch | Deployment | Log storage |
| kibana | Deployment | Log visualization |
| grafana | Deployment | Metrics dashboards |
| prometheus | Deployment | Metrics collector |
| ws-proxy | Deployment | WebSocket proxy |
| lamp-deployment | Deployment | LAMP stack |

### Docker (host)

| Component | Description |
|-----------|-------------|
| open-webui | Chat UI (port 8080) |
| ngrok | Tunnel to RAG API (systemd service) |

## LLM Pipeline (RAG Worker v9)

```
Query -> is_junk()? -> BLOCK (0 tokens)
      -> is_simple()? -> Redis Bank (db=5) -> 0 tokens
      -> Cache hit? -> Redis Cache (db=3) -> 0 tokens
      -> Default -> Cerebras LLM (llama3.1-8b) -> ~500 tokens
```

**Provider:** Cerebras | **Model:** llama3.1-8b | **Secret:** cerebras-api-key

## Repository Structure

```
k8s/
  aiot/              30 manifests (deployments, configmaps, secrets, ingress, cronjob)
  emqx/               5 manifests (emqx statefulset, mqtt-kafka-bridge)
  default/           13 manifests (grafana, kibana, elasticsearch, prometheus, ws-proxy, lamp)
src/
  rag-worker/         worker.py         - RAG Worker v9 (bank/cache/LLM routing)
  gateway/            gateway.py        - API Gateway (Cerebrus)
  digital-twin/       twin.py, twin_v3.py - Digital Twin engine
  sensor-simulator/   simulator.py      - IoT sensor data generator
  ngrok-proxy/        proxy.py          - Ngrok proxy
  pg-sink/            pg_sink.py        - PostgreSQL sink
  qdrant-indexer/     indexer.py        - Qdrant vector indexer
  redis-pg-flusher/   flusher.py        - Redis to PostgreSQL flusher
config/
  init.sql                              - PostgreSQL init schema
  pgadmin-servers.json                  - PgAdmin server config
scripts/
  ngrok.service                         - Systemd service for ngrok tunnel
  ngrok-update-webui.sh                 - Auto-updates ngrok URL in Open WebUI
  open-webui-docker.sh                  - Docker run script for Open WebUI
```

## Full Restore

### 1. Prerequisites

```bash
# Requires: Kubernetes cluster with ingress-nginx and longhorn storage class
kubectl create namespace aiot
kubectl create namespace emqx
```

### 2. Secrets

```bash
kubectl apply -f k8s/aiot/secret-cerebras-api-key.yaml
kubectl apply -f k8s/aiot/secret-pg-credentials.yaml
```

### 3. ConfigMaps

```bash
kubectl apply -f k8s/aiot/cm-*.yaml
kubectl apply -f k8s/emqx/cm-*.yaml
kubectl apply -f k8s/default/cm-*.yaml
```

### 4. StatefulSets (databases first)

```bash
kubectl apply -f k8s/aiot/ss-postgres.yaml
kubectl apply -f k8s/aiot/ss-redpanda.yaml
kubectl apply -f k8s/emqx/ss-emqx.yaml
# Wait for databases to be ready:
kubectl wait --for=condition=ready pod -l app=postgres -n aiot --timeout=120s
kubectl wait --for=condition=ready pod -l app=redpanda -n aiot --timeout=120s
```

### 5. Services

```bash
kubectl apply -f k8s/aiot/services.yaml
kubectl apply -f k8s/emqx/services.yaml
kubectl apply -f k8s/default/services.yaml
```

### 6. Deployments

```bash
kubectl apply -f k8s/aiot/deploy-*.yaml
kubectl apply -f k8s/emqx/deploy-*.yaml
kubectl apply -f k8s/default/deploy-*.yaml
```

### 7. Ingress and CronJobs

```bash
kubectl apply -f k8s/aiot/ingress.yaml
kubectl apply -f k8s/aiot/cj-pg-partition-mgr.yaml
```

### 8. Open WebUI + Ngrok (host level)

```bash
bash scripts/open-webui-docker.sh
sudo cp scripts/ngrok.service /etc/systemd/system/
sudo cp scripts/ngrok-update-webui.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/ngrok-update-webui.sh
sudo systemctl daemon-reload
sudo systemctl enable --now ngrok.service
```

## Quick Restore (single command)

```bash
git clone https://github.com/ondrejnr/k8s-cluster-backup.git && cd k8s-cluster-backup
kubectl create ns aiot && kubectl create ns emqx
kubectl apply -f k8s/aiot/secret-*.yaml
kubectl apply -f k8s/aiot/cm-*.yaml && kubectl apply -f k8s/emqx/cm-*.yaml && kubectl apply -f k8s/default/cm-*.yaml
kubectl apply -f k8s/aiot/ss-*.yaml && kubectl apply -f k8s/emqx/ss-*.yaml
kubectl apply -f k8s/aiot/services.yaml && kubectl apply -f k8s/emqx/services.yaml && kubectl apply -f k8s/default/services.yaml
kubectl apply -f k8s/aiot/deploy-*.yaml && kubectl apply -f k8s/emqx/deploy-*.yaml && kubectl apply -f k8s/default/deploy-*.yaml
kubectl apply -f k8s/aiot/ingress.yaml && kubectl apply -f k8s/aiot/cj-*.yaml
bash scripts/open-webui-docker.sh
```

## Access URLs

| Service | URL |
|---------|-----|
| Open WebUI | http://localhost:8080 |
| Cerebrus API | http://cerebrus.YOUR_IP.nip.io |
| RAG API | http://rag.YOUR_IP.nip.io |
| PgAdmin | http://pgadmin.YOUR_IP.nip.io |
| Ngrok (external) | https://[dynamic].ngrok-free.dev |
