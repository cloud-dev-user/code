from kafka import KafkaConsumer
import redis
import json

consumer = KafkaConsumer(
    'claim-events',
    bootstrap_servers='kafka:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

r = redis.Redis(host='redis', port=6379, decode_responses=True)

for message in consumer:
    data = message.value
    claim_id = data['claimId']
    amount = int(data['amount'])

    if amount > 100000:
        status = "REJECTED"
    else:
        status = "APPROVED"

    r.hset(f"claim:{claim_id}", mapping={
        "status": status,
        "amount": amount
    })

    print(f"{claim_id} → {status}")