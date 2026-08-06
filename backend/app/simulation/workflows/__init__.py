from app.simulation.workflows.ecommerce import ECOMMERCE

WORKFLOWS = {ECOMMERCE.name: ECOMMERCE}


def get_workflow(name: str):
    try:
        return WORKFLOWS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown workflow '{name}'. Available: {', '.join(WORKFLOWS)}") from exc
