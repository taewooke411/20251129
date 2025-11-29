# Black-Scholes Option Calculator

A lightweight Flask web app that prices options with a Monte Carlo Black-Scholes model. Enter standard model parameters and any payoff expression that uses the terminal price variable `ST` (e.g., `maximum(ST - 100, 0)`).

## Setup

1. Install dependencies (Python 3.10+ recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Start the web server:

   ```bash
   python app.py
   ```

   The app runs at <http://localhost:5000> by default.

## Usage

1. Open the web page and fill in:
   - **Spot price (S0)**: Current asset price.
   - **Risk-free rate (r)**: Continuously compounded annual rate.
   - **Volatility (σ)**: Annualized volatility.
   - **Time to maturity** (years).
   - **Number of simulations**: Monte Carlo paths.
   - **Payoff expression**: Any expression in terms of `ST`. Supported functions include `maximum`, `minimum`, `where`, `exp`, and `log` from `numexpr`.

2. Click **Calculate**. The app simulates log-normal terminal prices under the risk-neutral measure and returns the discounted expected payoff.

3. Example payoffs:
   - European call: `maximum(ST - 100, 0)`
   - European put: `maximum(110 - ST, 0)`
   - Digital call: `where(ST > 100, 1, 0)`

## Notes

- Inputs are validated for positivity where appropriate.
- Errors in the payoff expression are shown on the page without crashing the server.
