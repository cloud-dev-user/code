from kafka import KafkaConsumer
import redis
import json

consumer = KafkaConsumer(
    'claim-events',
    bootstrap_servers='kafka:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='earliest',
    group_id='claim-group'
)

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

        print(f"{claim_id} → {status}", flush=True)

    except Exception as e:
        print("Error processing message:", e, flush=True)