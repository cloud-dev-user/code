from flask import Flask, request, jsonify
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable
import redis
import json
import time

app = Flask(__name__)

def create_producer(retries=10, delay=5):
    for attempt in range(1, retries + 1):
        try:
            return KafkaProducer(
                bootstrap_servers='kafka:9092',
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        except NoBrokersAvailable:
            print(f"Kafka not ready (attempt {attempt}/{retries}), retrying in {delay}s...", flush=True)
            time.sleep(delay)
    raise RuntimeError("Could not connect to Kafka after retries")

producer = create_producer()

r = redis.Redis(host='redis', port=6379, decode_responses=True)

# CREATE CLAIM (WRITE → Kafka)
@app.route('/claim', methods=['POST'])
def create_claim():
    data = request.json
    producer.send('claim-events', data)
    return jsonify({"message": "Claim submitted"})

# GET CLAIM (READ → Redis)
@app.route('/claim/<claim_id>', methods=['GET'])
def get_claim(claim_id):
    data = r.hgetall(f"claim:{claim_id}")
    return jsonify(data)

# LIST ALL CLAIMS (READ → Redis)
@app.route('/claims', methods=['GET'])
def list_claims():
    limit = request.args.get('limit', type=int)
    if limit:
        ids = r.lrange("claim:log", -limit, -1)
        claims = []
        for claim_id in ids:
            data = r.hgetall(f"claim:{claim_id}")
            if data:
                data["claim_id"] = claim_id
                claims.append(data)
    else:
        keys = r.keys("claim:*")
        claims = []
        for key in sorted(keys):
            claim_id = key.split(":", 1)[1]
            data = r.hgetall(key)
            data["claim_id"] = claim_id
            claims.append(data)
    return jsonify(claims)

app.run(host="0.0.0.0", port=5000)