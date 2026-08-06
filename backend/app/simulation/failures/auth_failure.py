from app.simulation.failures.base import Failure
from app.simulation.models import LogStep

AUTH_FAILURE = Failure(
    name="auth_failure",
    description="Repeated bad credentials during login trip an account lockout.",
    steps=[
        LogStep(0.0, "auth-service", "WARNING", "Invalid credentials provided"),
        LogStep(0.7, "auth-service", "WARNING", "Invalid credentials provided (attempt 3)"),
        LogStep(1.3, "auth-service", "ERROR", "Repeated failed login attempts detected"),
        LogStep(1.8, "auth-service", "ERROR", "Account locked due to suspicious activity"),
        LogStep(2.2, "api-gateway", "ERROR", "401 Unauthorized returned to client"),
    ],
)
