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

---

## hub.go.kr 건축물대장 반복 조회 (Sheet1/full_address 기준)

요청하신 형태(엑셀 `sheet1`의 `full_address` 컬럼)로 자동 조회하도록 `hub_batch_scraper.py`를 구성했습니다.

- 입력 예시 주소: `경기도 광주시 신현동 1233-1`
- 자동 분해 항목: `시도`, `시군구`, `읍면동`, `본번`, `부번`
- 사이트에서 `검색` 클릭 후 결과 테이블을 읽어 최종 `.xlsx`로 저장

### 실행

```bash
python hub_batch_scraper.py \
  --input "C:/Users/taewo/Desktop/Koda_dataframe.xlsx" \
  --output "C:/Users/taewo/Desktop/Koda_result.xlsx" \
  --sheet-name "Sheet1" \
  --address-column "full_address"
```

### 주요 옵션

- `--wait-ms 1500`: 검색 클릭 후 추가 대기 시간(ms)
- `--headed`: 브라우저를 띄워 동작 확인
- `--selector-config selectors.sample.json`: 사이트 DOM 변경 시 셀렉터 보정

### 준비

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

> 참고: 사이트 구조가 바뀌면 기본 셀렉터가 실패할 수 있습니다. 이때 `--headed` 모드로 화면을 확인하고 `selectors.sample.json`을 수정해서 맞추면 됩니다.
