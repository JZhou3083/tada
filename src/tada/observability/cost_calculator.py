import yaml
from pathlib import Path

_pricing = None

def _load_pricing() -> dict:
    global _pricing
    path = Path(__file__).parent / "pricing.yaml"

    if _pricing is None:
        with open(path) as f:
            _pricing = yaml.safe_load(f)["pricing"]
    return _pricing


COST_COMPONENTS = [
(
"cached_input_cost_per_1m",
lambda u: u.get("cached_content_token_count") or 0
),
(
"input_cost_per_1m",
lambda u: (u.get("prompt_token_count") or 0) - (u.get("cached_content_token_count") or 0)
),
(
"thoughts_cost_per_1m",
lambda u: u.get("thoughts_token_count") or 0
),
(
"output_cost_per_1m",
lambda u: u.get("candidates_token_count") or 0 # Vertex: thoughts excluded already
),
]

def calculate_cost(model_name: str, usage: dict) -> dict:
    pricing = _load_pricing()

    model_pricing = pricing.get(model_name) or next(
    (v for k, v in pricing.items() if model_name.startswith(k)), None
    )

    if model_pricing is None:
        return {"error": f"No pricing for {model_name}", "total_cost_usd": 0.0}

    breakdown = {}
    total = 0.0

    for rate_key, token_fn in COST_COMPONENTS:
        rate = model_pricing.get(rate_key)
        tokens = token_fn(usage)
        cost = (tokens / 1000000) * rate if (tokens and rate) else 0.0
        breakdown[rate_key.replace("_cost_per_1m", "")] = {
        "tokens": tokens,
        "cost": round(cost, 6),
        }
        total += cost

    return {"model": model_name, "breakdown": breakdown, "total_cost_usd": round(total, 6)}

