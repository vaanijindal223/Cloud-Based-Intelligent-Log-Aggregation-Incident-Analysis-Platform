from app.simulation.failures.base import Failure
from app.simulation.models import LogStep

PAYMENT_API_TIMEOUT = Failure(
    name="payment_api_timeout",
    description="The payment gateway call during checkout stalls and times out.",
    steps=[
        LogStep(0.0, "payment-service", "INFO", "Charging card for order"),
        LogStep(1.0, "payment-service", "WARNING", "Payment gateway response slow (3200ms)"),
        LogStep(2.2, "payment-service", "ERROR", "Payment gateway request timeout after 5000ms"),
        LogStep(2.7, "order-service", "ERROR", "Order failed - payment not confirmed"),
        LogStep(3.1, "api-gateway", "ERROR", "504 Gateway Timeout returned"),
    ],
)
