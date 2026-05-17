from datetime import datetime
import logging
import math
import os
import time
import requests
from coins.prices import Price, PriceListing


def get_latest() -> PriceListing:
    api_key = os.getenv("COINMARKETCAP_API_KEY", "")
    results = requests.get(
        "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
        headers={"X-CMC_PRO_API_KEY": api_key},
    )

    logging.getLogger().info(
        f"status_code={results.status_code}, at_time={time.time()}"
    )
    as_json = results.json()

    return _parse_response(as_json)


def _parse_response(result_json: dict) -> PriceListing:
    prices_per_coin: dict[str, list[Price]] = {}

    for coin_data in result_json.get("data", []):
        coin = coin_data["symbol"]
        price = coin_data["quote"]["USD"]["price"]
        timestamp = datetime.strptime(
            coin_data["quote"]["USD"]["last_updated"], "%Y-%m-%dT%H:%M:%S.%fZ"
        ).timestamp()

        price_entry = Price(timestamp=math.floor(timestamp), price=price)

        prices_per_coin.setdefault(coin, [])
        prices_per_coin[coin].append(price_entry)

    return PriceListing(prices_per_coin=prices_per_coin)
