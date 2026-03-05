import json, time, logging, hashlib, math
from kafka import KafkaConsumer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("qdrant-indexer")
KAFKA_BROKER = "redpanda.aiot.svc.cluster.local:9092"
QDRANT_URL = "http://qdrant.aiot.svc.cluster.local:6333"
VECTOR_SIZE = 64
def safe_deserialize(x):
    try:
        return json.loads(x.decode("utf-8"))
    except Exception:
        return None
def simple_embed(text):
    vec = []
    for i in range(VECTOR_SIZE):
        h = hashlib.md5(f"{text}{i}".encode()).hexdigest()
        vec.append((int(h[:8], 16) / 0xFFFFFFFF) * 2 - 1)
    norm = math.sqrt(sum(x*x for x in vec))
    return [x/norm for x in vec]
qdrant = QdrantClient(url=QDRANT_URL)
try:
    qdrant.create_collection(
        collection_name="sensor_history",
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    )
    log.info("Collection sensor_history created")
except Exception as e:
    log.info(f"Collection exists: {e}")
consumer = KafkaConsumer(
    "telemetry",
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=safe_deserialize,
    group_id="qdrant-indexer-group4",
    auto_offset_reset="earliest"
)
log.info("Qdrant indexer started")
point_id = int(time.time())
for msg in consumer:
    data = msg.value
    if data is None:
        log.warning(f"Skipping non-JSON message on partition {msg.partition} offset {msg.offset}")
        continue
    try:
        payload = data.get("payload", {})
        topic = data.get("topic", "unknown")
        sid = payload.get("sensor_id") or payload.get("machine_id", "unknown")
        loc = payload.get("location") or payload.get("machine_type", "unknown")
        val = payload.get("value") or payload.get("temperature", 0)
        unit = payload.get("unit") or payload.get("status", "")
        text = f"Sensor {sid} at {loc} reported {val} {unit} on topic {topic}"
        embedding = simple_embed(text)
        qdrant.upsert(
            collection_name="sensor_history",
            points=[PointStruct(id=point_id, vector=embedding,
                payload={"text": text, "data": payload, "topic": topic, "timestamp": time.time()})]
        )
        point_id += 1
        log.info(f"Indexed: {text[:80]}")
    except Exception as e:
        log.error(f"Error processing message: {e}")
