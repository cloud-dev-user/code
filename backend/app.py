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

app.run(host="0.0.0.0", port=5000)