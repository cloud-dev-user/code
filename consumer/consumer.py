from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
import redis
import json
import time

def create_consumer(retries=10, delay=5):
    for attempt in range(1, retries + 1):
        try:
            return KafkaConsumer(
                'claim-events',
                bootstrap_servers='kafka:9092',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='claim-group'
            )
        except NoBrokersAvailable:
            print(f"Kafka not ready (attempt {attempt}/{retries}), retrying in {delay}s...", flush=True)
            time.sleep(delay)
    raise RuntimeError("Could not connect to Kafka after retries")

consumer = create_consumer()

r = redis.Redis(host='redis', port=6379, decode_responses=True)

for message in consumer:
    try:
        data = message.value
        print("Received:", data, flush=True)

        # ✅ Handle schema inconsistency
        claim_id = data.get("claimId") or data.get("claim_id")
        amount = int(data.get("amount", 0))

        if not claim_id:
            print("Invalid message: missing claim_id", flush=True)
            continue

        # ✅ Business logic
        if amount > 100000:
            status = "REJECTED"
        else:
            status = "APPROVED"

        # ✅ Store in Redis
        r.hset(f"claim:{claim_id}", mapping={
            "status": status,
            "amount": amount
        })
        r.rpush("claim:log", claim_id)

        print(f"{claim_id} → {status}", flush=True)

    except Exception as e:
        print("Error processing message:", e, flush=True)