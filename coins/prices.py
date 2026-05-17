from pydantic import BaseModel


class Price(BaseModel):
    timestamp: int
    price: float


class PriceListing(BaseModel):
    prices_per_coin: dict[str, list[Price]]
