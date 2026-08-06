from app.simulation.failures.base import Failure
from app.simulation.models import LogStep

DISK_FULL = Failure(
    name="disk_full",
    description="Disk fills up on the app host, then writes start failing.",
    steps=[
        LogStep(0.0, "monitoring-agent", "WARNING", "Disk usage at 90%"),
        LogStep(1.2, "monitoring-agent", "WARNING", "Disk usage at 95%"),
        LogStep(2.2, "monitoring-agent", "ERROR", "Disk usage critical - 100% full"),
        LogStep(2.7, "order-service", "ERROR", "Database write failed - no space left on device"),
        LogStep(3.2, "api-gateway", "ERROR", "Internal Server Error - write failure"),
    ],
)
