# Diagnostic Booking & Payment Service

![Tests](https://github.com/OmRajput17/eve-assessment/actions/workflows/tests.yml/badge.svg)

**Live API:** https://eve-assessment.onrender.com  
**Swagger docs:** https://eve-assessment.onrender.com/docs

> Note: hosted on Render's free tier — the service sleeps after inactivity, so the first request may take 30–60 seconds to respond.

A backend service for diagnostic test bookings and simulated payments, built with **FastAPI + SQLAlchemy 2.0 + PostgreSQL + JWT**.

Built for the EVE Healthcare backend assessment.

Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`); install uv before following the run instructions below.

---

## Architecture

```
HTTP request
   │
   ▼
 Routers (api/routes)      → parse/validate input (Pydantic), call a service, shape the response
   │
   ▼
 Services (services/)      → business rules, transactions, state transitions
   │
   ▼
 Repositories              → all SQL lives here (no SQL in services/routes)
   │
   ▼
 Models (models/)          → SQLAlchemy tables + domain behaviour (Booking state machine)
```

**Design principles:**

| Principle | Where it shows up |
|---|---|
| Single Responsibility | Routers = HTTP, Services = rules, Repositories = queries |
| Dependency Inversion | `PaymentService` depends on a `PaymentGateway` Protocol, not a concrete class |
| Encapsulation | Booking state changes only through `Booking.transition_to()` |
| Open/Closed | Swap `SimulatedPaymentGateway` for a real gateway without touching the service |
| Fail-fast | Custom exception hierarchy → consistent JSON error responses |
| Idempotency | Unique `event_id` constraint in DB + single-transaction webhook processing |

---

## How to Run Locally

### Option A — Docker (recommended, no local Postgres needed)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Copy the example env file and fill in real values (see [Environment Variables](#environment-variables) below):
   ```bash
   cp .env.example .env
   ```
3. Start everything:
   ```bash
   docker compose up --build
   ```
4. API is live at `http://localhost:8000`. Interactive Swagger docs at `http://localhost:8000/docs`.
5. Run the test suite (SQLite in-memory, no Postgres required):
   ```bash
   docker compose exec api uv run pytest -v
   ```

### Option B — Local Python with uv, Postgres in Docker

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Start only Postgres:
   ```bash
   docker compose up db -d
   ```
3. Set `DATABASE_URL` in `.env` to use `localhost` instead of `db`:
   ```
   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/eve
   ```
4. Install dependencies and run:
   ```bash
   uv sync
   uv run uvicorn app.main:app --reload
   ```
5. Run tests:
   ```bash
   uv run pytest -v
   ```

---

## Environment Variables

| Variable | Example | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@db:5432/eve` | Use host `db` under Docker Compose, `localhost` when running the app outside Docker |
| `JWT_SECRET` | random hex string | Generate with `openssl rand -hex 32` or `python -c "import secrets; print(secrets.token_hex(32))"`. Never reuse the placeholder. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime |
| `WEBHOOK_SECRET` | random hex string | Shared secret used to HMAC-sign webhook requests. Generate the same way as `JWT_SECRET`. |
| `PAYMENT_SUCCESS_RATE` | `0.8` | Probability an unforced simulated payment succeeds (0.0–1.0) |
| `ALLOW_PAYMENT_OVERRIDE` | `true` | If true, `POST /payments/` accepts `force_status: "SUCCESS" \| "FAILED"` for deterministic testing |
| `ADMIN_EMAILS` | `["admin@example.com"]` | JSON array. Any signup using one of these emails becomes an admin. |

`.env` is git-ignored — never commit real secrets.

---

## API Endpoints

All responses use a consistent error shape:
```json
{ "error": { "code": "not_found", "message": "Booking not found" } }
```

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | none | Register a new user |
| POST | `/auth/login` | none | Get a JWT access token |
| GET | `/auth/me` | user | Current user's profile |
| GET | `/centres` | none | List centres (supports `?location=`, `?limit=`, `?offset=`) |
| GET | `/centres/{id}` | none | Get one centre with its test offerings and prices |
| POST | `/centres` | admin | Create a centre |
| POST | `/tests` | admin | Create a test in the catalogue |
| GET | `/tests` | none | List tests (paginated) |
| POST | `/centres/{id}/tests` | admin | Add a priced offering (test) to a centre |
| POST | `/bookings/` | user | Book a test at a centre for a future date/time |
| GET | `/bookings/` | user | List the caller's own bookings (paginated) |
| GET | `/bookings/{id}` | user (owner) | Get one of the caller's own bookings |
| POST | `/bookings/{id}/cancel` | user (owner) | Cancel a booking |
| POST | `/payments/` | user (owner) | Simulate a payment for a booking |
| POST | `/payments/webhook/` | HMAC signature | Idempotent payment-status update from the (simulated) provider |

### Example requests (curl)

```bash
# Signup
curl -X POST localhost:8000/auth/signup -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","full_name":"Admin","password":"password123"}'

# Login
curl -X POST localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}'
export TOKEN=<access_token>

# Admin: create a centre, a test, and price it
curl -X POST localhost:8000/centres -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"City Labs","location":"Lucknow"}'
curl -X POST localhost:8000/tests -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"CBC","description":"Complete blood count"}'
curl -X POST localhost:8000/centres/1/tests -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"test_id":1,"price":"499.00"}'

# Browse (public)
curl "localhost:8000/centres?location=lucknow&limit=10&offset=0"

# Book a test
curl -X POST localhost:8000/bookings/ -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"centre_id":1,"test_id":1,"appointment_at":"2030-01-15T10:00:00Z"}'

# Pay (simulated, forced outcome for deterministic testing)
curl -X POST localhost:8000/payments/ -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"booking_id":1,"force_status":"SUCCESS"}'

# Pay asynchronously — stays PENDING until the webhook confirms it
curl -X POST localhost:8000/payments/ -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"booking_id":1,"async_mode":true}'

# Cancel a booking (no request body required)
curl -X POST localhost:8000/bookings/1/cancel -H "Authorization: Bearer $TOKEN"

# Simulate the provider calling the webhook (HMAC-SHA256 over the raw body)
BODY='{"event_id":"evt_1001","provider_reference":"sim_xxx","status":"SUCCESS"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')
curl -X POST localhost:8000/payments/webhook/ -H "Content-Type: application/json" -H "X-Signature: $SIG" -d "$BODY"
# Sending the exact same request again returns {"outcome":"duplicate"} and changes nothing.
```

---

## Database / Schema Design

```
users(id PK, email UQ, full_name, hashed_password, is_admin, created_at)

diagnostic_centres(id PK, name, location IDX, created_at)

diagnostic_tests(id PK, name UQ, description, created_at)

centre_tests(id PK, centre_id FK, test_id FK, price NUMERIC(10,2),
             UQ(centre_id, test_id), CHECK price > 0)

bookings(id PK, user_id FK, centre_id, test_id, appointment_at, amount, status,
         FK(centre_id, test_id) → centre_tests(centre_id, test_id))

payments(id PK, booking_id FK, amount, status, provider_reference UQ, created_at)

webhook_events(id PK, event_id UQ, provider_reference, payload JSON, created_at)
```

**Key design decisions:**

- **Price lives on the join table (`centre_tests`), not on the test itself** — the same test costs different amounts at different centres.
- **Bookings store a price snapshot** (`amount`), computed server-side from the offering at the moment of booking. A client can never set its own price, and later price changes never retroactively alter past bookings.
- **A booking can have multiple payments.** A failed attempt followed by a successful retry is kept as history (two rows), rather than overwriting one payment row — this gives a real audit trail.
- **The composite foreign key** `(centre_id, test_id) → centre_tests` guarantees at the database level that a booking can only be made for a test a centre actually offers.
- **`webhook_events` with a `UNIQUE(event_id)` constraint** is the idempotency guard — it makes duplicate-event protection race-safe even under concurrent identical requests, not just "check-then-insert" logic in application code.
- **`NUMERIC(10,2)`** is used for all money fields — never `float` — to avoid rounding errors.

**Booking state machine:**

```
PENDING ──payment success──► CONFIRMED ──► CANCELLED
   │                              ▲
   ├──payment fails──► FAILED ────┘ (retry allowed)
   └────────────────► CANCELLED
```

Transitions are enforced in one place — `Booking.transition_to()` — so no code path can put a booking into an invalid state. `CANCELLED` is terminal.

---

## Important Assumptions

- Prices are set **per centre per test**; a booking stores a **price snapshot** taken at booking time.
- A booking covers exactly one test at one centre. There is no appointment-slot or capacity management.
- Admins are bootstrapped via the `ADMIN_EMAILS` setting; there is no self-service way for a regular signup to become admin.
- A `FAILED` booking can be paid again (retry). A `CONFIRMED` booking can only be cancelled, not re-paid.
- Webhook requests are authenticated with an HMAC-SHA256 signature over the raw request body, using a shared secret (`WEBHOOK_SECRET`) — simulating how a real payment provider (Stripe, Razorpay, etc.) would sign webhook payloads.
- A webhook event for a payment that is already settled (SUCCESS or FAILED) is acknowledged but **ignored** — this prevents a late or out-of-order event from flipping a final state (e.g. a delayed `FAILED` event can never downgrade an already-`CONFIRMED` booking).
- Fetching or acting on a booking that belongs to another user returns `404`, not `403` — this avoids leaking which booking IDs exist to users who don't own them.
- Cancelling a `CONFIRMED` booking does not trigger an automatic refund; this is out of scope and would be logged/flagged for manual/automated follow-up in a real system.
- Tables are created at application startup via SQLAlchemy's `create_all` for simplicity; a production system would use Alembic migrations instead.

---

## What I'd Improve With More Time

1. **Alembic migrations** instead of `create_all`, for safe, versioned schema changes.
2. **Celery + Redis** for webhook processing with exponential-backoff retries and a dead-letter queue, instead of processing synchronously in the request.
3. **Redis caching** for centre/test listings (cache-aside pattern, invalidated on admin writes).
4. **Rate limiting** on `/auth/login` and `/payments/` to reduce brute-force and abuse risk.
5. **Idempotency-Key header** on `POST /payments/` itself, in addition to webhook idempotency, so a retried client request can't create two payment attempts.
6. **A proper refund flow** for cancelled/confirmed bookings, plus a background job to auto-cancel bookings whose payment has stayed `PENDING` too long.
7. **Slot/capacity management** per centre and time window, to prevent double-booking the same appointment slot.
8. **Refresh tokens**, password reset, and email verification for a production-grade auth flow.
9. **Request-ID middleware** so every log line for a single request can be correlated end-to-end.
10. **CI pipeline** (lint, type-check, test) via GitHub Actions, plus integration tests run against a real PostgreSQL instance rather than SQLite.

---

## Tests

```bash
uv run pytest -v
```

31 tests covering:
- Auth: signup, duplicate-email conflict, validation errors, wrong-password rejection, protected-route auth
- Bookings: server-side pricing, past-date rejection, invalid centre/test combinations, ownership isolation (404 on another user's booking), admin-only catalogue writes
- Payments: success/failure/retry flow, double-payment prevention, cross-user access rejection
- Webhooks: idempotent duplicate handling, bad-signature rejection, unknown-reference handling, invalid payload validation, late-failure-does-not-downgrade-success
- Booking state machine: every allowed and forbidden transition, tested in isolation with no database

Tests run against an in-memory SQLite database, so no Postgres instance is required to run the suite. Row-level locking (`SELECT ... FOR UPDATE`) and the unique-constraint race protection on webhook events are real safeguards that apply on PostgreSQL in production/Docker use, though SQLite does not exercise the locking behavior itself.

The test suite also runs automatically on every push via GitHub Actions — see the badge at the top of this file and the workflow definition at `.github/workflows/tests.yml`.

---

## Testing Admin Endpoints (Live Deployment)

Admin access is granted automatically to any user who signs up with an email listed in the `ADMIN_EMAILS` environment variable — there is no manual role-assignment step. On the live deployment, this list includes a neutral demo address so a reviewer can self-serve admin access without needing anyone's personal credentials:

```
ADMIN_EMAILS=["demo-admin@example.com", ...]
```

To test admin-only endpoints (creating centres, tests, and priced offerings), sign up with this exact email against the live API:

```bash
curl -X POST https://eve-assessment.onrender.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"demo-admin@example.com","full_name":"Demo Admin","password":"any-password-you-like"}'
```

Then log in to get a token, and use it for the admin routes exactly as shown in the [Example requests](#example-requests-curl) section above (just replace `localhost:8000` with `https://eve-assessment.onrender.com`):

```bash
curl -X POST https://eve-assessment.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo-admin@example.com","password":"any-password-you-like"}'
```

---

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (SQLAlchemy 2.0 ORM, `psycopg` v3 driver)
- **Auth:** JWT (PyJWT), bcrypt password hashing
- **Validation:** Pydantic v2
- **Package management:** [uv](https://docs.astral.sh/uv/)
- **Testing:** pytest + httpx (FastAPI `TestClient`)
- **Containerization:** Docker + Docker Compose
- **API docs:** Auto-generated OpenAPI/Swagger at `/docs`