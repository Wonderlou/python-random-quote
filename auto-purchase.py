#!/usr/bin/env python3
"""Automate a purchase workflow against an HTTP API.

The script is intentionally defensive:
- Dry-run mode is enabled by default.
- It validates stock and price before creating an order.
- It supports polling until timeout for flash-sale scenarios.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error, request


@dataclass
class PurchaseConfig:
    base_url: str
    product_id: str
    quantity: int
    max_price: float
    timeout_seconds: int = 60
    poll_interval_seconds: float = 3.0
    auth_token_env: str = "PURCHASE_API_TOKEN"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PurchaseConfig":
        required = ["base_url", "product_id", "quantity", "max_price"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"Missing required config fields: {', '.join(missing)}")

        return cls(
            base_url=str(data["base_url"]).rstrip("/"),
            product_id=str(data["product_id"]),
            quantity=int(data["quantity"]),
            max_price=float(data["max_price"]),
            timeout_seconds=int(data.get("timeout_seconds", 60)),
            poll_interval_seconds=float(data.get("poll_interval_seconds", 3.0)),
            auth_token_env=str(data.get("auth_token_env", "PURCHASE_API_TOKEN")),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate a purchase task via HTTP API")
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to JSON config file",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create the order. Without this flag the script only simulates.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def http_json(
    method: str,
    url: str,
    token: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    headers = {"Accept": "application/json"}
    body = None

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url=url, method=method, data=body, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} on {method} {url}: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error on {method} {url}: {exc}") from exc


def fetch_product(config: PurchaseConfig, token: Optional[str]) -> Dict[str, Any]:
    url = f"{config.base_url}/products/{config.product_id}"
    return http_json("GET", url, token=token)


def create_order(config: PurchaseConfig, token: Optional[str]) -> Dict[str, Any]:
    url = f"{config.base_url}/orders"
    payload = {"product_id": config.product_id, "quantity": config.quantity}
    return http_json("POST", url, token=token, payload=payload)


def can_purchase(product: Dict[str, Any], config: PurchaseConfig) -> bool:
    stock = int(product.get("stock", 0))
    price = float(product.get("price", float("inf")))

    if stock < config.quantity:
        logging.info("Stock not enough: need %s, got %s", config.quantity, stock)
        return False

    if price > config.max_price:
        logging.info("Price too high: %.2f > %.2f", price, config.max_price)
        return False

    logging.info("Purchase condition met: stock=%s, price=%.2f", stock, price)
    return True


def run(config: PurchaseConfig, execute: bool) -> int:
    import os

    token = os.getenv(config.auth_token_env)
    if not token:
        logging.warning("No API token found in %s. Proceeding unauthenticated.", config.auth_token_env)

    deadline = time.monotonic() + config.timeout_seconds

    while time.monotonic() < deadline:
        product = fetch_product(config, token)
        logging.debug("Product payload: %s", product)

        if can_purchase(product, config):
            if not execute:
                logging.info("Dry-run mode: would create order now. Use --execute to place it.")
                return 0

            order = create_order(config, token)
            logging.info("Order created successfully: %s", order)
            return 0

        time.sleep(config.poll_interval_seconds)

    logging.error("Timeout reached without matching purchase conditions.")
    return 1


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    config_data = json.loads(args.config.read_text(encoding="utf-8"))
    config = PurchaseConfig.from_dict(config_data)

    if config.quantity <= 0:
        raise ValueError("quantity must be > 0")

    if config.max_price <= 0:
        raise ValueError("max_price must be > 0")

    return run(config, execute=args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
