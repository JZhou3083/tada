class CostError(Exception):
    """Base class for cost calculation errors."""

    error_type: str = "cost_error"


class PricingNotFoundError(CostError):
    error_type = "pricing_not_found"


class InvalidUsageError(CostError):
    error_type = "invalid_usage"


class CalculationError(CostError):
    error_type = "calculation_error"
