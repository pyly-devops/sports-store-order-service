import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import orders_collection
from observability import configure_logging, instrument
from routes import orders

# Before anything else in this module can log, so no line escapes as plain
# text during import.
configure_logging()

logger = logging.getLogger("order-service")

app = FastAPI(title="Sports Store — Order Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# AFTER add_middleware, deliberately. Starlette builds its middleware stack so
# that the last one added is the outermost, so registering here means the
# metrics middleware wraps CORS rather than sitting inside it — and the
# latency histogram measures the whole request as a client experiences it.
instrument(app)

app.include_router(orders.router, prefix="/api")


@app.on_event("startup")
async def create_indexes():
    try:
        await orders_collection.create_index("order_number", unique=True)
        await orders_collection.create_index([("user_id", 1), ("created_at", -1)])
        await orders_collection.create_index("status")
    except Exception as exc:  # Mongo may be unavailable (e.g. unit tests)
        logger.warning("Index creation skipped: %s", exc)


@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}
