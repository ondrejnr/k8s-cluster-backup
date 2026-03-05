import json, time, logging, threading
from kafka import KafkaConsumer
from flask import Flask, jsonify
import redis

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("digital-twin")

KAFKA_BROKER = "redpanda.aiot.svc.cluster.local:9092"
r = redis.Redis(host="redis-master.aiot.svc.cluster.local", port=6379, db=4, decode_responses=True)
app = Flask(__name__)

LIMITS = {
    "pump":       {"temperature": (20,60),  "vibration": (0,2.0), "pressure": (70,115), "rpm": (800,1800)},
    "compressor": {"temperature": (20,80),  "vibration": (0,3.0), "pressure": (70,150), "rpm": (800,2000)},
    "motor":      {"temperature": (20,75),  "vibration": (0,2.5), "pressure": (0,999),  "rpm": (500,2500)},
    "conveyor":   {"temperature": (20,50),  "vibration": (0,1.5), "pressure": (0,999),  "rpm": (200,1200)},
    "turbine":    {"temperature": (20,100), "vibration": (0,4.0), "pressure": (70,200), "rpm": (1000,3500)},
}

def check_metrics(machine_type, payload):
    limits = LIMITS.get(machine_type, {})
    violations = []
    for metric, (mn, mx) in limits.items():
        val = payload.get(metric)
        if val is None:
            continue
        val = float(val)
        if val > mx:
            violations.append({"metric": metric, "value": round(val,2), "limit": mx, "type": "HIGH"})
        elif val < mn:
            violations.append({"metric": metric, "value": round(val,2), "limit": mn, "type": "LOW"})
    return violations

def get_status(violations, anomaly_score):
    if float(anomaly_score or 0) > 0.7:
        return "CRITICAL"
    if len(violations) >= 2:
        return "CRITICAL"
    if len(violations) == 1:
        return "WARNING"
    return "OK"

def consume():
    consumer = KafkaConsumer(
        "telemetry",
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        group_id="digital-twin-group4",
        auto_offset_reset="latest"
    )
    log.info("Digital twin multi-metric consumer started")
    for msg in consumer:
        try:
            data = msg.value
            payload = data.get("payload", {})
            machine_id = payload.get("machine_id") or payload.get("sensor_id", "unknown")
            machine_type = payload.get("machine_type") or payload.get("location", "unknown")
            anomaly_score = float(payload.get("anomaly_score") or 0)
            violations = check_metrics(machine_type, payload)
            status = get_status(violations, anomaly_score)
            twin = {
                "machine_id": machine_id,
                "machine_type": machine_type,
                "status": status,
                "violations": violations,
                "metrics": {
                    "temperature":   payload.get("temperature"),
                    "vibration":     payload.get("vibration"),
                    "pressure":      payload.get("pressure"),
                    "rpm":           payload.get("rpm"),
                    "humidity":      payload.get("humidity"),
                    "anomaly_score": anomaly_score
                },
                "limits": LIMITS.get(machine_type, {}),
                "topic": data.get("topic", ""),
                "updated_at": time.time()
            }
            r.hset("digital-twin:machines", machine_id, json.dumps(twin))
            r.setex("digital-twin:last-update", 60, str(time.time()))
            prev_raw = r.hget("digital-twin:prev-status", machine_id)
            prev_status = json.loads(prev_raw)["status"] if prev_raw else "OK"
            if status != "OK":
                if status != prev_status:
                    alert = {
                        "machine_id": machine_id,
                        "machine_type": machine_type,
                        "status": status,
                        "violations": violations,
                        "anomaly_score": anomaly_score,
                        "metrics": twin["metrics"],
                        "ts": time.time()
                    }
                    r.lpush("digital-twin:alerts", json.dumps(alert))
                    r.ltrim("digital-twin:alerts", 0, 49)
                    log.warning("ALERT " + status + ": " + machine_id + " violations=" + str(len(violations)) + " " + str([v["metric"] for v in violations]))
            else:
                log.info("OK: " + machine_id + " (" + machine_type + ")" +
                    " T=" + str(payload.get("temperature")) +
                    " V=" + str(payload.get("vibration")) +
                    " P=" + str(payload.get("pressure")) +
                    " RPM=" + str(payload.get("rpm")))
            r.hset("digital-twin:prev-status", machine_id, json.dumps({"status": status}))
        except Exception as e:
            log.error("Consume error: " + str(e))

@app.route("/twin")
def get_twin():
    machines = r.hgetall("digital-twin:machines")
    result = {k: json.loads(v) for k, v in machines.items()}
    critical = [k for k,v in result.items() if v["status"] == "CRITICAL"]
    warning  = [k for k,v in result.items() if v["status"] == "WARNING"]
    ok       = [k for k,v in result.items() if v["status"] == "OK"]
    return jsonify({
        "machines": result,
        "count": len(result),
        "summary": {
            "ok": len(ok),
            "warning": len(warning),
            "critical": len(critical),
            "critical_machines": critical,
            "warning_machines": warning
        },
        "timestamp": time.time()
    })

@app.route("/twin/<machine_id>")
def get_machine(machine_id):
    data = r.hget("digital-twin:machines", machine_id)
    if not data:
        return jsonify({"error": "not found"}), 404
    return jsonify(json.loads(data))

@app.route("/alerts")
def get_alerts():
    alerts = r.lrange("digital-twin:alerts", 0, 49)
    return jsonify({
        "count": len(alerts),
        "alerts": [json.loads(a) for a in alerts]
    })

@app.route("/health")
def health():
    last = r.get("digital-twin:last-update")
    age = time.time() - float(last) if last else 999
    machines = r.hgetall("digital-twin:machines")
    result = {k: json.loads(v) for k, v in machines.items()}
    critical = [k for k,v in result.items() if v["status"] == "CRITICAL"]
    warning  = [k for k,v in result.items() if v["status"] == "WARNING"]
    return jsonify({
        "status": "ok" if age < 30 else "stale",
        "data_age_seconds": round(age, 1),
        "machines_monitored": len(result),
        "critical": len(critical),
        "warning": len(warning)
    })

threading.Thread(target=consume, daemon=True).start()
log.info("Digital Twin multi-metric API on port 8001")
app.run(host="0.0.0.0", port=8001)
