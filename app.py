import math
from dataclasses import dataclass
from typing import Tuple

import numexpr as ne
import numpy as np
from flask import Flask, render_template, request


@dataclass
class PricingInput:
    spot: float
    rate: float
    volatility: float
    maturity: float
    simulations: int
    payoff: str


def draw_terminal_prices(inputs: PricingInput, rng: np.random.Generator) -> np.ndarray:
    drift = (inputs.rate - 0.5 * inputs.volatility ** 2) * inputs.maturity
    diffusion = inputs.volatility * math.sqrt(inputs.maturity)
    shocks = rng.standard_normal(inputs.simulations)
    return inputs.spot * np.exp(drift + diffusion * shocks)


def evaluate_payoff(expression: str, terminal_prices: np.ndarray) -> np.ndarray:
    """Safely evaluate the payoff expression for a vector of terminal prices."""
    allowed_names = {"ST": terminal_prices}
    try:
        payoff = ne.evaluate(expression, local_dict=allowed_names)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid payoff expression: {exc}") from exc

    if np.isscalar(payoff):
        return np.full_like(terminal_prices, payoff, dtype=float)
    return np.asarray(payoff, dtype=float)


def price_option(inputs: PricingInput, seed: int | None = None) -> Tuple[float, np.ndarray]:
    rng = np.random.default_rng(seed)
    terminal_prices = draw_terminal_prices(inputs, rng)
    payoff = evaluate_payoff(inputs.payoff, terminal_prices)
    discounted = np.exp(-inputs.rate * inputs.maturity) * payoff
    return float(np.mean(discounted)), terminal_prices


def parse_inputs(form_data: dict) -> PricingInput:
    try:
        return PricingInput(
            spot=float(form_data.get("spot", 100)),
            rate=float(form_data.get("rate", 0.01)),
            volatility=float(form_data.get("volatility", 0.2)),
            maturity=float(form_data.get("maturity", 1.0)),
            simulations=int(form_data.get("simulations", 10000)),
            payoff=form_data.get("payoff", "maximum(ST - 100, 0)"),
        )
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("All numerical inputs must be valid numbers.") from exc


def validate_inputs(inputs: PricingInput) -> None:
    if inputs.spot <= 0:
        raise ValueError("Spot price must be positive.")
    if inputs.volatility <= 0:
        raise ValueError("Volatility must be positive.")
    if inputs.maturity <= 0:
        raise ValueError("Time to maturity must be positive.")
    if inputs.simulations <= 0:
        raise ValueError("Simulations must be a positive integer.")
    if not inputs.payoff.strip():
        raise ValueError("Payoff expression cannot be empty.")


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    context: dict = {
        "result": None,
        "error": None,
        "inputs": PricingInput(100.0, 0.01, 0.2, 1.0, 10000, "maximum(ST - 100, 0)"),
    }

    if request.method == "POST":
        try:
            context["inputs"] = parse_inputs(request.form)
            validate_inputs(context["inputs"])
            price, _ = price_option(context["inputs"])
            context["result"] = price
        except ValueError as exc:
            context["error"] = str(exc)

    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
