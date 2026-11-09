
"""Independent API gateway and recommendation inference service."""

import os
import time
import secrets

from uuid import UUID, uuid4
from typing import Literal
from urllib.parse import quote

import httpx

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import Response

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST
)

from .storage import Store, Conflict
from .cache import Cache
from .hybrid import Hybrid, PRODUCTS


# ==================================================
# INITIALIZATION
# ==================================================

app = FastAPI(
    title="Recommendation Platform",
    version="3.0"
)

store = Store()
cache = Cache()
model = Hybrid()

role = os.getenv("APP_ROLE", "api")

requests = Counter(
    "platform_requests_total",
    "HTTP responses",
    ["role", "method", "status"]
)

latency = Histogram(
    "platform_request_seconds",
    "HTTP latency",
    ["role"]
)


# ==================================================
# MONITORING
# ==================================================

@app.middleware("http")
async def observe(request, call_next):

    start = time.perf_counter()
    status = 500

    try:
        response = await call_next(request)
        status = response.status_code
        return response

    finally:

        requests.labels(
            role,
            request.method,
            str(status)
        ).inc()

        latency.labels(role).observe(
            time.perf_counter() - start
        )


@app.get("/metrics")
def metrics():

    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ==================================================
# HEALTH CHECKS
# ==================================================

@app.get("/health")
@app.get("/live")
def live():

    return {
        "status": "ok",
        "service": role
    }


@app.get("/ready")
def ready():

    try:

        with store.engine.connect() as connection:

            connection.execute(
                text(
                    "SELECT version FROM signal_versions WHERE id=1"
                )
            ).scalar_one()

        return {"status": "ready"}

    except Exception as exc:

        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}"
        )


# ==================================================
# EVENT MODEL
# ==================================================

class Event(BaseModel):

    event_id: UUID = Field(default_factory=uuid4)

    user_id: str = Field(
        min_length=1,
        max_length=100
    )

    product_id: str

    event_type: Literal[
        "view",
        "click",
        "purchase"
    ]

    dwell_seconds: float = Field(
        default=0,
        ge=0,
        le=36000,
        allow_inf_nan=False
    )

    @field_validator("user_id")
    @classmethod
    def validate_user(cls, value):

        value = value.strip()

        if not value:
            raise ValueError("Blank user")

        return value


# ==================================================
# RECOMMENDATIONS
# ==================================================

@app.get("/recommendations/{user_id}")
def recommendations(
    user_id: str,
    limit: int = 5,
    refresh: int = 0
):
    limit = min(5, len(PRODUCTS))
    refresh = max(0, refresh)

    # API GATEWAY
    if role == "api":

        try:

            recommendation_url = (
                os.getenv(
                    "RECOMMENDATION_URL",
                    "http://recommendation:8000"
                )
                + "/recommendations/"
                + quote(user_id, safe="")
            )

            response = httpx.get(
                recommendation_url,
                params={"limit": limit, "refresh": refresh},
                timeout=10
            )

            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as exc:

            raise HTTPException(
                status_code=503,
                detail=f"Recommendation service unavailable: {exc}"
            )

    # RECOMMENDATION ENGINE
    version, history, signals = store.model_snapshot(user_id)

    # Include the model version, event version and manual refresh seed in the cache key.
    key = cache.key(
        user_id,
        limit,
        "hybrid-v4-" + str(version) + "-refresh-" + str(refresh)
    )

    result = cache.get(key)

    if result is None:

        result = {
            "user_id": user_id,
            "signal_version": version,
            "recommendations": model.recommend(
                history,
                signals,
                limit,
                refresh_seed=refresh
            )
        }

        cache.put(key, result)

    return result


# ==================================================
# API GATEWAY ROUTES
# ==================================================

if role == "api":

    # PRODUCT CATALOGUE
    @app.get("/products")
    def products():

        return PRODUCTS

    # RECORD INTERACTION
    @app.post("/events")
    def accept(event: Event):

        if event.product_id not in model.index:

            raise HTTPException(
                status_code=404,
                detail="Unknown product"
            )

        try:

            created = store.accept(
                event.model_dump(mode="json")
            )

        except Conflict as exc:

            raise HTTPException(
                status_code=409,
                detail=str(exc)
            )

        return {
            "message": "event accepted",
            "event": event.model_dump(mode="json"),
            "created": created,
            "published_to_broker": False,
            "publication_status": "accepted; processing asynchronously"
        }

    # USER HISTORY
    @app.get("/events/{user_id}")
    def history(
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ):

        return store.history(
            user_id,
            limit,
            offset
        )

    # TRENDING
    @app.get("/trending")
    def trending():

        _, _, signals = store.model_snapshot("")

        return model.recommend(
            [],
            signals,
            12,
            mode="popularity"
        )

    # ADMIN ANALYTICS
    @app.get("/admin/analytics")
    def analytics(
        x_admin_key: str = Header(default="")
    ):

        configured = os.getenv("ADMIN_KEY", "")

        if (
            not configured
            or not secrets.compare_digest(
                configured,
                x_admin_key
            )
        ):

            raise HTTPException(
                status_code=401,
                detail="Admin key required"
            )

        return store.analytics()

    # SYSTEM STATUS
    @app.get("/system")
    def system():

        result = {
            "api": "up",
            "database": "down",
            "redis": "down",
            "recommendation": "down"
        }

        try:

            ready()
            result["database"] = "up"

        except Exception:
            pass

        try:

            cache.client.ping()
            result["redis"] = "up"

        except Exception:
            pass

        try:

            response = httpx.get(
                os.getenv(
                    "RECOMMENDATION_URL",
                    "http://recommendation:8000"
                ) + "/ready",
                timeout=2
            )

            if response.is_success:
                result["recommendation"] = "up"

        except Exception:
            pass

        return result


# ==================================================
# TELEMETRY
# ==================================================

from .telemetry import configure

configure(app)
