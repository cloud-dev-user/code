#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[startup]${NC} $1"; }
warn() { echo -e "${YELLOW}[startup]${NC} $1"; }
fail() { echo -e "${RED}[startup]${NC} $1"; exit 1; }

APISIX_ADMIN="http://localhost:9180/apisix/admin"
ADMIN_KEY="edd1c9f034335f136f87ad84b625c8f1"

# ---------------------------------------------------------------------------
# 1. Start all containers
# ---------------------------------------------------------------------------
log "Starting all services..."
docker-compose up --build -d

# ---------------------------------------------------------------------------
# 2. Wait for APISIX Admin API to be ready
# ---------------------------------------------------------------------------
log "Waiting for APISIX admin API..."
for i in $(seq 1 30); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-API-KEY: $ADMIN_KEY" \
    "$APISIX_ADMIN/routes")
  if [[ "$CODE" == "200" ]]; then
    log "APISIX admin API is up."
    break
  fi
  warn "  attempt $i/30 (got: $CODE) — retrying in 3s..."
  sleep 3
  if [[ "$i" -eq 30 ]]; then
    fail "APISIX did not become ready. Check: docker-compose logs apisix"
  fi
done

# Give etcd a moment to fully sync with APISIX before writing routes
sleep 3

# ---------------------------------------------------------------------------
# 3. Register APISIX routes
# ---------------------------------------------------------------------------
log "Registering route: POST /claim"
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PUT "$APISIX_ADMIN/routes/1" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/claim",
    "methods": ["POST", "OPTIONS"],
    "plugins": {
      "cors": {
        "allow_origins": "*",
        "allow_methods": "POST, OPTIONS",
        "allow_headers": "Content-Type"
      }
    },
    "upstream": {
      "type": "roundrobin",
      "nodes": { "backend:5000": 1 }
    }
  }')
[[ "$CODE" == 2* ]] || fail "POST /claim route registration failed (HTTP $CODE)"
log "  POST /claim registered (HTTP $CODE)"

log "Registering route: GET /claim/*"
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PUT "$APISIX_ADMIN/routes/2" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/claim/*",
    "methods": ["GET", "OPTIONS"],
    "plugins": {
      "cors": {
        "allow_origins": "*",
        "allow_methods": "GET, OPTIONS",
        "allow_headers": "Content-Type"
      }
    },
    "upstream": {
      "type": "roundrobin",
      "nodes": { "backend:5000": 1 }
    }
  }')
[[ "$CODE" == 2* ]] || fail "GET /claim/* route registration failed (HTTP $CODE)"
log "  GET /claim/* registered (HTTP $CODE)"

log "Registering route: GET /claims"
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PUT "$APISIX_ADMIN/routes/3" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/claims",
    "methods": ["GET", "OPTIONS"],
    "plugins": {
      "cors": {
        "allow_origins": "*",
        "allow_methods": "GET, OPTIONS",
        "allow_headers": "Content-Type"
      }
    },
    "upstream": {
      "type": "roundrobin",
      "nodes": { "backend:5000": 1 }
    }
  }')
[[ "$CODE" == 2* ]] || fail "GET /claims route registration failed (HTTP $CODE)"
log "  GET /claims registered (HTTP $CODE)"

# ---------------------------------------------------------------------------
# 4. Wait for backend to be reachable through the gateway
# ---------------------------------------------------------------------------
log "Waiting for backend to be reachable via gateway..."
for i in $(seq 1 20); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:9080/claim \
    -H "Content-Type: application/json" \
    -d '{"claim_id":"healthcheck","amount":1,"type":"test"}')
  if [[ "$CODE" == 2* ]]; then
    log "Backend is reachable (HTTP $CODE)."
    break
  fi
  warn "  attempt $i/20 (got: $CODE) — retrying in 3s..."
  sleep 3
  if [[ "$i" -eq 20 ]]; then
    warn "Backend not reachable yet — check: docker-compose logs backend"
  fi
done

# ---------------------------------------------------------------------------
# 5. Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Stack is up and configured${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  UI              →  http://localhost:8080"
echo "  API Gateway     →  http://localhost:9080"
echo "  APISIX Admin    →  http://localhost:9180"
echo "  Backend (direct)→  http://localhost:5000"
echo ""
echo "  Logs:   docker-compose logs -f [consumer|backend|apisix]"
echo "  Stop:   docker-compose down"
echo ""
