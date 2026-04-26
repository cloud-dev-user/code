# Insurance Claims Processing System

A demo **CQRS + Event-Driven Architecture** system for insurance claim submission and processing.

---

## Architecture Overview

**Pattern:** Command Query Responsibility Segregation (CQRS) + Event-Driven Architecture

### Components

| Component | Technology | Port | Role |
|-----------|-----------|------|------|
| UI | Nginx + HTML/JS | 8080 | Frontend — submit claims, view dashboard |
| API Gateway | Apache APISIX | 9080 / 9180 | Single entry point, routes all traffic |
| Config Store | etcd | 2379 | APISIX configuration backend |
| Backend | Python Flask | 5000 | Command (write) + Query (read) API |
| Message Broker | Apache Kafka | 9092 | Async event stream (`claim-events` topic) |
| Coordination | Zookeeper | 2181 | Kafka cluster coordination |
| Read Store | Redis | 6379 | Fast query store for processed claims |
| Consumer | Python (headless) | — | Event processor — Kafka → business logic → Redis |

---

## Data Flow

### Write Path (Command)

```
User → UI → APISIX (9080) → Backend POST /claim → Kafka topic: claim-events
                                                          ↓
                                                    Consumer reads event
                                                          ↓
                                              Business logic: amount > 100,000?
                                                    REJECTED : APPROVED
                                                          ↓
                                               Redis HSET claim:{id}
```

### Read Path (Query)

```
User → UI → APISIX (9080) → Backend GET /claim/{id} → Redis HGETALL → JSON response → UI
```

### Architecture Diagram

```
[Browser UI]
     |
     | HTTP (port 9080)
     ▼
[APISIX API Gateway] ←── config ──── [etcd]
     |
     | proxy
     ▼
[Flask Backend]
   |         |
   | POST     | GET
   ▼         ▼
[Kafka]    [Redis] ◄──── [Consumer]
  ↓                           ↑
  └──── claim-events ─────────┘
         (async stream)
```

---

## Business Logic

The Consumer service processes every claim event from Kafka:

- Accepts both `claimId` and `claim_id` field names (schema tolerance)
- **Amount > 100,000 → Status: REJECTED**
- **Amount ≤ 100,000 → Status: APPROVED**
- Persists `{ status, amount }` to Redis key `claim:{claim_id}`

---

## API Endpoints

All requests go through the APISIX gateway at `http://localhost:9080`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/claim` | Submit a new claim (async — writes to Kafka) |
| GET | `/claim/{claim_id}` | Fetch claim status (reads from Redis) |

### POST /claim — Request Body

```json
{
  "claim_id": "c101",
  "amount": 50000,
  "type": "hospital"
}
```

### GET /claim/{claim_id} — Response

```json
{
  "status": "APPROVED",
  "amount": "50000"
}
```

---

## Key Design Decisions

1. **CQRS split** — Writes go to Kafka (async, decoupled); Reads come from Redis (fast, synchronous)
2. **APISIX as gateway** — All UI calls go to port 9080; backend is never directly exposed
3. **Stateless backend** — No local DB; backend delegates all state to Kafka and Redis
4. **Async processing** — Claim submission returns immediately; status is available after the consumer processes the event
5. **etcd** — Powers APISIX's dynamic routing config (traditional deployment mode)

---

## Project Structure

```
.
├── apisix_conf/
│   └── config.yaml       # APISIX gateway configuration
├── backend/
│   └── app.py            # Flask API — POST (Kafka producer) + GET (Redis reader)
├── consumer/
│   └── consumer.py       # Kafka consumer — business logic + Redis writer
├── ui/
│   └── index.html        # Frontend — claim submission + dashboard
└── docker-compose.yaml   # Full stack orchestration
```

---

## Quick Start

See [SETUP.md](SETUP.md) for full installation and configuration instructions.

```bash
docker-compose up --build
```

Open [http://localhost:8080](http://localhost:8080) to access the UI.
