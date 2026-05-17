from sqlmodel import Field, SQLModel


class CoinConfidence(SQLModel, table=True):
    __tablename__ = "coins_confidence"
    coin_name: str = Field(primary_key=True, nullable=False)
    period: int = Field(primary_key=True, nullable=False)
    confidence: float = Field(default=0.0)

class Exchange(SQLModel, table=True):
    __tablename__ = "exchanges"
    coin_name: str = Field(primary_key=True)
    timestamp: int = Field(primary_key=True)
    value: float = Field(nullable=False, default=0.0)