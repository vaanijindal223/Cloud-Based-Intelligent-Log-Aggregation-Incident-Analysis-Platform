from app.simulation.failures.base import Failure
from app.simulation.models import LogStep

REDIS_FAILURE = Failure(
    name="redis_failure",
    description="The session cache becomes unreachable during checkout, breaking auth.",
    steps=[
        LogStep(0.0, "cache-service", "WARNING", "Redis response slow (620ms)"),
        LogStep(0.9, "cache-service", "ERROR", "Redis connection refused"),
        LogStep(1.5, "auth-service", "ERROR", "Session store unavailable - session lost"),
        LogStep(2.0, "auth-service", "ERROR", "Login failed - unable to validate session"),
    ],
)
