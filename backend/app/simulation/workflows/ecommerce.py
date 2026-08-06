from app.simulation.models import LogStep
from app.simulation.workflows.base import Workflow

ECOMMERCE = Workflow(
    name="ecommerce",
    description="Login, browse products, add to cart, start checkout.",
    steps=[
        LogStep(0.0, "auth-service", "INFO", "User login successful"),
        LogStep(0.8, "catalog-service", "INFO", "Product search completed (24 results)"),
        LogStep(1.6, "cart-service", "INFO", "Item added to cart"),
        LogStep(2.4, "order-service", "INFO", "Checkout started"),
    ],
)
