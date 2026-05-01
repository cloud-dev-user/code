# Setup Guide — Insurance Claims Processing System

---

## Prerequisites

Install the following before proceeding:

| Tool | Version | Download |
|------|---------|----------|
| Docker | 20.x or later | https://docs.docker.com/get-docker/ |
| Docker Compose | v2.x or later | Included with Docker Desktop |
| Git | Any | https://git-scm.com/ |

Verify installations:

```bash
docker --version
docker compose version
```

---

## 1. Clone the Repository

```bash
git clone <repository-url>
cd <project-folder>
```

---

## 2. Start All Services

### Option A — Automated (recommended)

```bash
chmod +x startup.sh
./startup.sh
```

`startup.sh` handles everything: starts containers, waits for APISIX to be ready, registers both API routes, and confirms the backend is reachable.

### Option B — Manual

```bash
docker-compose up --build -d
```

Then follow steps 3 and 4 below to verify and configure routes.

> First run will pull Docker images (~1–2 GB). Subsequent starts are fast.

---

## 3. Verify Services Are Running

```bash
docker-compose ps
```

Expected output — all services should show `Up`:

```
NAME         IMAGE                              STATUS
zookeeper    confluentinc/cp-zookeeper:7.5.0   Up
kafka        confluentinc/cp-kafka:7.5.0        Up
redis        redis:7                            Up
etcd         quay.io/coreos/etcd:v3.5.9         Up
apisix       apache/apisix:3.6.0-debian         Up
backend      python:3.9                         Up
consumer     python:3.9                         Up
ui           nginx:alpine                       Up
```

---

## 4. Configure APISIX Routes

APISIX starts without routes. You must register the backend routes via the Admin API before the system works end-to-end.

Run these two `curl` commands (or use a REST client like Postman/Insomnia):

### Route 1 — POST /claim (Submit Claim)

```bash
curl -X PUT http://localhost:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/claim",
    "methods": ["POST"],
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "backend:5000": 1
      }
    }
  }'
```

### Route 2 — GET /claim/:id (Fetch Claim Status)

```bash
curl -X PUT http://localhost:9180/apisix/admin/routes/2 \
  -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/claim/*",
    "methods": ["GET"],
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "backend:5000": 1
      }
    }
  }'
```

> The Admin API key `edd1c9f034335f136f87ad84b625c8f1` is defined in `apisix_conf/config.yaml`.

---

## 5. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| UI (Frontend) | http://localhost:8080 | Claims submission + dashboard |
| APISIX Gateway | http://localhost:9080 | API entry point |
| APISIX Admin API | http://localhost:9180 | Route management |
| Backend (direct) | http://localhost:5000 | Flask API (bypass gateway) |
| Redis | localhost:6379 | Redis CLI access |
| Kafka | localhost:9092 | Kafka broker |

---

## 6. Test the System

### Submit a claim via curl

```bash
curl -X POST http://localhost:9080/claim \
  -H "Content-Type: application/json" \
  -d '{"claim_id": "c101", "amount": 50000, "type": "hospital"}'
```

Expected response:
```json
{"message": "Claim submitted"}
```

### Wait 1–2 seconds for the consumer to process, then fetch the status:

```bash
curl http://localhost:9080/claim/c101
```

Expected response:
```json
{"amount": "50000", "status": "APPROVED"}
```

### Test rejection (amount > 100,000):

```bash
curl -X POST http://localhost:9080/claim \
  -H "Content-Type: application/json" \
  -d '{"claim_id": "c102", "amount": 150000, "type": "travel"}'

curl http://localhost:9080/claim/c102
```

Expected: `{"amount": "150000", "status": "REJECTED"}`

---

## 7. View Logs

### All services:
```bash
docker-compose logs -f
```

### Specific service:
```bash
docker-compose logs -f consumer   # Watch claim processing
docker-compose logs -f backend    # Watch API requests
docker-compose logs -f apisix     # Watch gateway traffic
```

---

## 8. Stop the Stack

```bash
docker-compose down
```

To also remove volumes (clears all Redis data and Kafka topics):

```bash
docker-compose down -v
```

---

## Troubleshooting

### APISIX returns 404 for /claim
Routes have not been registered. Re-run the curl commands in Step 4.

### Backend fails to connect to Kafka on startup
Kafka takes ~15–20 seconds to become ready. The backend may exit and restart a few times — this is normal. Wait for it to stabilize.

### Consumer shows "Invalid message: missing claim_id"
The submitted payload is missing both `claim_id` and `claimId` fields. Ensure your POST body includes one of these.

### UI shows no claims in the dashboard
The hardcoded demo IDs are `c101`, `c103`, `c104`, `c105`. Submit claims using these IDs to see them appear in the dashboard.

### Redis data inspection
```bash
docker exec -it redis redis-cli
> HGETALL claim:c101
```

### Kafka topic inspection
```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic claim-events \
  --from-beginning
```

---

## Port Reference

| Port | Service |
|------|---------|
| 8080 | UI (Nginx) |
| 9080 | APISIX Gateway |
| 9180 | APISIX Admin API |
| 5000 | Flask Backend |
| 6379 | Redis |
| 9092 | Kafka |
| 2181 | Zookeeper |
| 2379 | etcd |
