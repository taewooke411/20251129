from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from playwright.sync_api import Locator, Page, TimeoutError, sync_playwright

TARGET_URL = "https://www.hub.go.kr/portal/opn/tyb/idx-bdrg-ttlldr.do"


@dataclass
class ParsedAddress:
    full_address: str
    sido: str
    sigungu: str
    eupmyeondong: str
    bun: str
    ji: str


@dataclass
class SelectorConfig:
    sido_select_candidates: list[str]
    sigungu_select_candidates: list[str]
    eupmyeondong_select_candidates: list[str]
    bun_input_candidates: list[str]
    ji_input_candidates: list[str]
    search_button_candidates: list[str]
    result_ready_candidates: list[str]
    field_selectors: dict[str, str]

    @staticmethod
    def default() -> "SelectorConfig":
        return SelectorConfig(
            sido_select_candidates=[
                "select[name*='ctprvn']",
                "select[id*='ctprvn']",
                "select[name*='sido']",
                "select[id*='sido']",
                "label:has-text('대지위치') >> xpath=.. >> select >> nth=0",
            ],
            sigungu_select_candidates=[
                "select[name*='signgu']",
                "select[id*='signgu']",
                "select[name*='sigungu']",
                "select[id*='sigungu']",
                "label:has-text('대지위치') >> xpath=.. >> select >> nth=1",
            ],
            eupmyeondong_select_candidates=[
                "select[name*='emd']",
                "select[id*='emd']",
                "select[name*='dong']",
                "select[id*='dong']",
                "label:has-text('대지위치') >> xpath=.. >> select >> nth=2",
            ],
            bun_input_candidates=[
                "input[name*='bonbun']",
                "input[id*='bonbun']",
                "input[name*='bun']",
                "input[id*='bun']",
                "label:has-text('대지위치') >> xpath=.. >> input >> nth=0",
            ],
            ji_input_candidates=[
                "input[name*='bubun']",
                "input[id*='bubun']",
                "input[name*='ji']",
                "input[id*='ji']",
                "label:has-text('대지위치') >> xpath=.. >> input >> nth=1",
            ],
            search_button_candidates=[
                "button:has-text('검색')",
                "button:has-text('조회')",
                "a:has-text('검색')",
                "button[type='submit']",
                "input[type='submit']",
            ],
            result_ready_candidates=["table", ".tb_list", ".tb_view", ".result", ".search_result"],
            field_selectors={},
        )


def load_selector_config(path: Path | None) -> SelectorConfig:
    if path is None:
        return SelectorConfig.default()
    payload = json.loads(path.read_text(encoding="utf-8"))
    default = SelectorConfig.default()
    return SelectorConfig(
        sido_select_candidates=payload.get("sido_select_candidates", default.sido_select_candidates),
        sigungu_select_candidates=payload.get("sigungu_select_candidates", default.sigungu_select_candidates),
        eupmyeondong_select_candidates=payload.get(
            "eupmyeondong_select_candidates", default.eupmyeondong_select_candidates
        ),
        bun_input_candidates=payload.get("bun_input_candidates", default.bun_input_candidates),
        ji_input_candidates=payload.get("ji_input_candidates", default.ji_input_candidates),
        search_button_candidates=payload.get("search_button_candidates", default.search_button_candidates),
        result_ready_candidates=payload.get("result_ready_candidates", default.result_ready_candidates),
        field_selectors=payload.get("field_selectors", default.field_selectors),
    )


def parse_full_address(full_address: str) -> ParsedAddress:
    parts = re.split(r"\s+", full_address.strip())
    if len(parts) < 4:
        raise ValueError(f"주소 형식 인식 실패: '{full_address}'")

    sido, sigungu, eupmyeondong = parts[0], parts[1], parts[2]
    lot_part = "".join(parts[3:])
    match = re.search(r"(?P<bun>\d+)(?:-(?P<ji>\d+))?", lot_part)
    if not match:
        raise ValueError(f"번지 인식 실패: '{full_address}'")

    return ParsedAddress(
        full_address=full_address,
        sido=sido,
        sigungu=sigungu,
        eupmyeondong=eupmyeondong,
        bun=match.group("bun"),
        ji=match.group("ji") or "",
    )


def pick_first_locator(page: Page, candidates: list[str], timeout_ms: int = 1800) -> Locator:
    for selector in candidates:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except TimeoutError:
            continue
    raise RuntimeError(f"셀렉터를 찾지 못했습니다: {candidates}")


def select_option_by_text(locator: Locator, text: str) -> None:
    try:
        locator.select_option(label=text)
        return
    except Exception:
        pass

    option_count = locator.locator("option").count()
    for i in range(option_count):
        option = locator.locator("option").nth(i)
        option_text = option.inner_text().strip()
        if text in option_text:
            value = option.get_attribute("value")
            if value is not None:
                locator.select_option(value=value)
                return
    raise RuntimeError(f"드롭다운에서 '{text}' 항목을 찾지 못했습니다.")


def extract_table_kv(page: Page) -> dict[str, str]:
    data = page.evaluate(
        """
        () => {
          const result = {};
          const tables = Array.from(document.querySelectorAll('table'));
          for (const table of tables) {
            const rows = Array.from(table.querySelectorAll('tr'));
            for (const row of rows) {
              const headers = row.querySelectorAll('th');
              const cells = row.querySelectorAll('td');
              if (headers.length >= 1 && cells.length >= 1) {
                for (let i = 0; i < headers.length; i++) {
                  const k = headers[i]?.innerText?.trim() || '';
                  const v = cells[i]?.innerText?.trim() || '';
                  if (k) result[k] = v;
                }
              }
            }
          }
          return result;
        }
        """
    )
    return {str(k): str(v) for k, v in data.items()}


def wait_result(page: Page, candidates: list[str], timeout_ms: int = 7000) -> None:
    each_timeout = max(int(timeout_ms / max(len(candidates), 1)), 1200)
    for sel in candidates:
        try:
            page.locator(sel).first.wait_for(state="attached", timeout=each_timeout)
            return
        except TimeoutError:
            continue
    page.wait_for_timeout(1200)


def scrape_once(page: Page, parsed: ParsedAddress, selectors: SelectorConfig, wait_ms: int) -> dict[str, Any]:
    page.goto(TARGET_URL, wait_until="domcontentloaded")

    sido_select = pick_first_locator(page, selectors.sido_select_candidates)
    sigungu_select = pick_first_locator(page, selectors.sigungu_select_candidates)
    eupmyeondong_select = pick_first_locator(page, selectors.eupmyeondong_select_candidates)
    bun_input = pick_first_locator(page, selectors.bun_input_candidates)
    ji_input = pick_first_locator(page, selectors.ji_input_candidates)
    search_button = pick_first_locator(page, selectors.search_button_candidates)

    select_option_by_text(sido_select, parsed.sido)
    page.wait_for_timeout(200)
    select_option_by_text(sigungu_select, parsed.sigungu)
    page.wait_for_timeout(200)
    select_option_by_text(eupmyeondong_select, parsed.eupmyeondong)

    bun_input.fill(parsed.bun)
    ji_input.fill(parsed.ji)

    search_button.click()
    wait_result(page, selectors.result_ready_candidates)

    if wait_ms > 0:
        page.wait_for_timeout(wait_ms)

    row: dict[str, Any] = {
        "full_address": parsed.full_address,
        "sido": parsed.sido,
        "sigungu": parsed.sigungu,
        "eupmyeondong": parsed.eupmyeondong,
        "bun": parsed.bun,
        "ji": parsed.ji,
        "scraped_at": int(time.time()),
        "page_url": page.url,
    }

    for output_key, css in selectors.field_selectors.items():
        locator = page.locator(css).first
        row[output_key] = locator.inner_text().strip() if locator.count() else ""

    kv = extract_table_kv(page)
    row.update(kv)
    row["raw_kv_json"] = json.dumps(kv, ensure_ascii=False)
    return row


def run_batch(
    input_path: Path,
    output_path: Path,
    sheet_name: str,
    address_column: str,
    selectors: SelectorConfig,
    wait_ms: int,
    headless: bool,
) -> None:
    frame = pd.read_excel(input_path, sheet_name=sheet_name)
    if address_column not in frame.columns:
        raise ValueError(f"'{sheet_name}' 시트에서 '{address_column}' 컬럼을 찾지 못했습니다.")

    addresses = (
        frame[address_column].dropna().astype(str).str.strip().loc[lambda s: s != ""].tolist()
    )

    results: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        for idx, address in enumerate(addresses, start=1):
            try:
                parsed = parse_full_address(address)
                row = scrape_once(page, parsed, selectors=selectors, wait_ms=wait_ms)
                row["status"] = "ok"
                row["error"] = ""
            except Exception as exc:  # noqa: BLE001
                row = {
                    "full_address": address,
                    "status": "error",
                    "error": str(exc),
                    "raw_kv_json": "{}",
                }
            results.append(row)
            print(f"[{idx}/{len(addresses)}] {address} -> {row['status']}")

        context.close()
        browser.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_excel(output_path, index=False)
    print(f"완료: {output_path} ({len(results)}건)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="hub.go.kr 건축물대장 대량 조회 자동화")
    parser.add_argument("--input", required=True, type=Path, help="입력 엑셀 경로")
    parser.add_argument("--output", required=True, type=Path, help="출력 엑셀 경로")
    parser.add_argument("--sheet-name", default="Sheet1", help="입력 시트명 (기본: Sheet1)")
    parser.add_argument(
        "--address-column",
        default="full_address",
        help="주소 컬럼명 (기본: full_address)",
    )
    parser.add_argument("--selector-config", type=Path, default=None, help="셀렉터 JSON 경로")
    parser.add_argument("--wait-ms", type=int, default=1200, help="검색 후 추가 대기시간(ms)")
    parser.add_argument("--headed", action="store_true", help="브라우저 표시 모드")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selectors = load_selector_config(args.selector_config)
    run_batch(
        input_path=args.input,
        output_path=args.output,
        sheet_name=args.sheet_name,
        address_column=args.address_column,
        selectors=selectors,
        wait_ms=args.wait_ms,
        headless=not args.headed,
    )


if __name__ == "__main__":
    main()
