def convert_fiat_to_crypto(
    exchange_rates: dict[str, float], coin_name: str, amount: float
) -> float:
    return amount / exchange_rates[coin_name]


def convert_crypto_to_fiat(
    exchange_rates: dict[str, float], coin_name: str, amount: float
) -> float:
    return round(amount * exchange_rates.get(coin_name, 0), 2)
