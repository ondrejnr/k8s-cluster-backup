<div align="center">

# AIoT Smart Factory Platform

### AI-Powered Industrial IoT Monitoring and Analytics

**418 machines** -- **2 LLM models** -- **Zero-token answers for 75% of queries** -- **Real-time MQTT to AI pipeline**

---
</div>

## AI-First Architecture

This platform processes **real-time industrial sensor data** through an AI pipeline
that combines **vector search**, **Redis-cached analytics**, and **dual LLM inference**
(Cerebras + Groq) to deliver instant factory insights.

```
                         +-------------------------------------+
                         |          Open WebUI (:8080)          |
                         |        Chat Interface (Docker)       |
                         +------+----------------+-------------+
                                |                |
                    +-----------+--+     +-------+----------+
                    | cerebrus-aiot|     |    groq-aiot      |
                    |   (:31700)   |     |    (:31090)       |
                    |  rag-worker  |     |   ngrok-proxy     |
                    +------+-------+     +------+-----------+
                           |                    |
                    +------+--------------------+------+
                    |        Redis BANK (DB5)          |
                    |   Pre-computed Analytics Cache    |
                    +------------------+---------------+
                                       | cache miss only
                           +-----------+-----------+
                           |    LLM Inference       |
                           |  Cerebras / Groq API   |
                           +------------------------+
```

## Bank-First Intelligence Pattern

The core innovation is the **Bank-First pattern** -- a Redis-cached analytics layer
that answers most factory queries **without any LLM API call**:

- **SIMPLE** queries (summary, status, count) --> Redis BANK --> **under 50ms, 0 tokens**
- **COMPLEX** queries (why, compare, recommend) --> LLM API --> ~500ms, with tokens
- **Result: ~75% of user queries consume zero tokens**

## Real-Time Data Pipeline

```
+----------------+     +--------------+     +--------------+
|   Sensor       |MQTT |    EMQX      |     |  Redpanda    |
|  Simulator     +---->|  (3 nodes)   +---->|   (Kafka)    |
|  418 machines  |:1883|  MQTT Broker |     |  Streaming   |
+----------------+     +--------------+     +------+-------+
                                                   |
                     +-----------------------------+---------------+
                     |                             |               |
              +------+------+            +---------+----+ +--------+-----+
              |   pg-sink   |            | mongo-sink   | |  qdrant-     |
              |  > Postgres |            | > MongoDB    | |  indexer     |
              +------+------+            +------+-------+ +------+------+
                     |                          |                |
              +------+------+            +------+-------+ +------+------+
              | PostgreSQL  |            |   MongoDB    | |   Qdrant    |
              |  Time-series|            |  Documents   | |  Vectors    |
              |    10 Gi    |            |    5 Gi      | |   15 Gi     |
              +------+------+            +--------------+ +-------------+
                     |
              +------+-----------+
              |  redis-pg-flusher|
              |  (3 replicas)    |
              |  Batch > Redis   |
              |  DB5 (BANK)      |
              +------------------+
```

## Data Flow

1. **Sensor Simulator** generates IoT data (temp, vibration, pressure, rpm) for 418 machines
2. **EMQX** (3-node MQTT cluster) receives and distributes messages
3. **MQTT-Kafka Bridge** forwards MQTT topics to Redpanda/Kafka
4. **pg-sink** writes time-series data to PostgreSQL
5. **mongo-sink** stores documents in MongoDB
6. **qdrant-indexer** creates vector embeddings in Qdrant
7. **redis-pg-flusher** (3 replicas) computes aggregates into Redis BANK (DB5)
8. **LLM layer** (rag-worker / ngrok-proxy) answers user questions using BANK data or LLM API

## Dual LLM Setup

Two independent LLM backends serve the same factory data:

- **cerebrus-aiot** (port 31700) -- Cerebras llama-4-scout via rag-worker (2 replicas)
- **groq-aiot** (port 31090) -- Groq llama-3.3-70b via ngrok-proxy (2 replicas)

Both share the same Redis BANK, same classification logic, same instant answers for simple queries.
They differ only in LLM reasoning for complex queries.
API keys stored as Kubernetes Secrets (not in this repo).

## High Availability

- api-gateway: 2 replicas + PDB (minAvailable: 1)
- ngrok-proxy: 2 replicas + PDB (minAvailable: 1)
- rag-worker: 2 replicas + PDB (minAvailable: 1)
- digital-twin: 2 replicas
- Redis: 3 nodes + 3 sentinels
- EMQX: 3 nodes
- redis-pg-flusher: 3 replicas
- Open WebUI: Docker restart=always

## Repository Structure

```
k8s/
  aiot/
    configmaps/       17 ConfigMaps (all application code)
    deployments/      15 Deployment manifests
    statefulsets/      4 StatefulSets (postgres, redis, redpanda, mongodb)
    services/         17 Services (NodePort + ClusterIP)
    cronjobs/          4 CronJobs (watchdog, partitions, cleanup, backup)
    pdb/               7 PodDisruptionBudgets
    pvc/              PersistentVolumeClaims (Piraeus storage)
    secrets/          Secret names only (values in K8s)
  emqx/
    emqx-statefulset.yaml    3-node EMQX cluster
    mqtt-kafka-bridge.yaml   MQTT to Kafka bridge (2 replicas)
    services.yaml
config/
  docker/open-webui.json     Open WebUI container config
  webui/webui-config.json    WebUI LLM connection settings
```

## Port Map

- 8080: Open WebUI (AI chat)
- 31700: cerebrus-aiot (Cerebras LLM)
- 31090: groq-aiot (Groq LLM)
- 31801: Digital Twin API
- 31883: EMQX MQTT
- 31379: Redis
- 31080: pgAdmin
- 30881: Mongo Express

## Automated Jobs

- **cluster-watchdog**: every 10 min -- cluster health check
- **pg-partition-mgr**: hourly -- PostgreSQL partition management
- **pg-sensor-cleanup**: every 5 min -- old sensor data pruning
- **postgres-backup**: every 6 hours -- PostgreSQL full backup

## Secrets (not in repo)

- cerebras-api-key (CEREBRAS_API_KEY) -- used by api-gateway
- groq-api-key (GROQ_API_KEY) -- used by ngrok-proxy
- pg-credentials (username, password) -- used by pg-sink, flusher

## Disaster Recovery

```bash
kubectl create namespace aiot
kubectl create secret generic cerebras-api-key -n aiot --from-literal=CEREBRAS_API_KEY=YOUR_KEY
kubectl create secret generic groq-api-key -n aiot --from-literal=GROQ_API_KEY=YOUR_KEY
kubectl create secret generic pg-credentials -n aiot --from-literal=POSTGRES_USER=USER --from-literal=POSTGRES_PASSWORD=PASS
kubectl apply -f k8s/aiot/configmaps/
kubectl apply -f k8s/aiot/pvc/
kubectl apply -f k8s/aiot/services/
kubectl apply -f k8s/aiot/statefulsets/
sleep 30
kubectl apply -f k8s/aiot/deployments/
kubectl apply -f k8s/aiot/cronjobs/
kubectl apply -f k8s/aiot/pdb/
kubectl create namespace emqx
kubectl apply -f k8s/emqx/
docker run -d --name open-webui --restart=always --network host -v open-webui:/app/backend/data ghcr.io/open-webui/open-webui:main
```

---
Backup date: 2026-03-15
