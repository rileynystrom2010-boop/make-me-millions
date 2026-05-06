from __future__ import annotations

import argparse
import socket
from dataclasses import dataclass

import requests

from app.alpaca_client import AlpacaPaperClient


DEFAULT_ENDPOINTS = {
    "Alpaca data": "https://data.alpaca.markets",
    "White House": "https://www.whitehouse.gov",
    "Treasury": "https://home.treasury.gov",
    "SEC": "https://www.sec.gov",
    "EIA": "https://www.eia.gov",
    "Federal Register": "https://www.federalregister.gov",
}


@dataclass(frozen=True)
class EndpointCheck:
    name: str
    host: str
    dns_ok: bool
    https_ok: bool
    message: str


def check_endpoint(name: str, url: str, timeout: float) -> EndpointCheck:
    host = url.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    try:
        socket.gethostbyname(host)
    except OSError as exc:
        return EndpointCheck(name, host, False, False, f"DNS failed: {exc}")

    try:
        response = requests.get(url, timeout=timeout)
        return EndpointCheck(
            name,
            host,
            True,
            response.status_code < 500,
            f"HTTP {response.status_code}",
        )
    except requests.RequestException as exc:
        return EndpointCheck(name, host, True, False, f"HTTPS failed: {exc}")


def run(timeout: float, include_alpaca_account: bool) -> int:
    print("Network diagnostics")
    for name, url in DEFAULT_ENDPOINTS.items():
        result = check_endpoint(name, url, timeout)
        status = "OK" if result.dns_ok and result.https_ok else "FAIL"
        print(f"{status} {result.name} ({result.host}): {result.message}")

    if include_alpaca_account:
        print()
        print(AlpacaPaperClient().check_connection())

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check network access for trading bot data sources")
    parser.add_argument("--timeout", type=float, default=5, help="Seconds to wait for each endpoint")
    parser.add_argument("--alpaca-account", action="store_true", help="Also check Alpaca paper account credentials")
    args = parser.parse_args()
    return run(timeout=args.timeout, include_alpaca_account=args.alpaca_account)


if __name__ == "__main__":
    raise SystemExit(main())
