from app.simulation.failures.base import Failure
from app.simulation.models import LogStep

DATABASE_TIMEOUT = Failure(
    name="database_timeout",
    description="The checkout write to the database degrades and times out, cascading into auth.",
    steps=[
        LogStep(0.0, "order-service", "WARNING", "Database response slow (480ms)"),
        LogStep(1.0, "order-service", "ERROR", "Database connection timeout"),
        LogStep(1.8, "order-service", "ERROR", "Database retry failed after 3 attempts"),
        LogStep(2.4, "cache-service", "ERROR", "Redis waiting on DB fallback, cache miss"),
        LogStep(2.9, "auth-service", "ERROR", "Authentication failed - DB unreachable"),
        LogStep(3.3, "api-gateway", "ERROR", "Upstream returned 503 Service Unavailable"),
    ],
)
