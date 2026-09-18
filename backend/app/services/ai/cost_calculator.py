from typing import Optional

class CostCalculator:
    """
    Centralized Cost Calculator for AI operations.
    Calculates estimated USD costs based on configurable model token pricing.
    Strictly returns None if tokens or pricing are unexposed.
    """

    # Pricing in USD per 1,000,000 tokens: (input_price_per_1M, output_price_per_1M)
    MODEL_PRICING: dict[str, tuple[float, float]] = {
        "gemini-2.5-flash": (0.075, 0.30),
        "gemini-1.5-flash": (0.075, 0.30),
        "gemini-1.5-pro": (3.50, 10.50),
        "gemini-pro": (0.50, 1.50),
        "BAAI/bge-small-en-v1.5": (0.00, 0.00),
        "bge-small": (0.00, 0.00),
    }

    @classmethod
    def calculate_cost(
        cls,
        provider: str,
        model: str,
        input_tokens: Optional[int],
        output_tokens: Optional[int]
    ) -> Optional[float]:
        """
        Calculates estimated USD cost.
        Returns None if tokens or model pricing are not available.
        """
        if input_tokens is None and output_tokens is None:
            return None

        # Clean model name (e.g. models/gemini-2.5-flash -> gemini-2.5-flash)
        clean_model = model.split("/")[-1].lower() if model else ""
        pricing = cls.MODEL_PRICING.get(clean_model)
        if not pricing:
            # Check prefix match (e.g. gemini-2.5-flash-preview)
            for k, v in cls.MODEL_PRICING.items():
                if clean_model.startswith(k):
                    pricing = v
                    break

        if not pricing:
            return None

        input_rate_per_million, output_rate_per_million = pricing
        inp = input_tokens or 0
        out = output_tokens or 0

        estimated_usd = (inp * input_rate_per_million + out * output_rate_per_million) / 1_000_000.0
        return round(estimated_usd, 6)

cost_calculator = CostCalculator()
