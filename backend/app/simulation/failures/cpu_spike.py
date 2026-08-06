from app.simulation.failures.base import Failure
from app.simulation.models import LogStep

CPU_SPIKE = Failure(
    name="cpu_spike",
    description="Host CPU exhaustion drives up response times until requests time out.",
    steps=[
        LogStep(0.0, "monitoring-agent", "WARNING", "CPU utilization at 85%"),
        LogStep(1.0, "monitoring-agent", "WARNING", "CPU utilization at 90%"),
        LogStep(2.0, "monitoring-agent", "ERROR", "CPU utilization critical at 98%"),
        LogStep(2.6, "order-service", "WARNING", "Response time increased to 2400ms"),
        LogStep(3.3, "api-gateway", "ERROR", "Request timeout - upstream service unresponsive"),
    ],
)
