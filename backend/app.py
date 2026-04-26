from flask import Flask, request, jsonify
from kafka import KafkaProducer
import redis
import json

app = Flask(__name__)

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

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