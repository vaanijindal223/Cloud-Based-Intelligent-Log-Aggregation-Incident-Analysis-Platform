from app.simulation.failures.auth_failure import AUTH_FAILURE
from app.simulation.failures.base import Failure
from app.simulation.failures.cpu_spike import CPU_SPIKE
from app.simulation.failures.database_timeout import DATABASE_TIMEOUT
from app.simulation.failures.disk_full import DISK_FULL
from app.simulation.failures.payment_api_timeout import PAYMENT_API_TIMEOUT
from app.simulation.failures.redis_failure import REDIS_FAILURE

NONE_FAILURE = Failure(name="none", description="Healthy run, no injected failure.", steps=[])

FAILURES = {
    f.name: f
    for f in [
        NONE_FAILURE,
        DATABASE_TIMEOUT,
        REDIS_FAILURE,
        PAYMENT_API_TIMEOUT,
        AUTH_FAILURE,
        CPU_SPIKE,
        DISK_FULL,
    ]
}


def get_failure(name: str) -> Failure:
    try:
        return FAILURES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown failure '{name}'. Available: {', '.join(FAILURES)}") from exc
