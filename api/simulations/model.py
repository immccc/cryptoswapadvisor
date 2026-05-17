from pydantic import BaseModel, Field


from typing import Dict

from webhooks.model import MessageSent


class SimulationResponse(BaseModel):
    current_fiat_balance: float = Field(..., description="Current balance in fiat currency.")
    amount_per_coins: Dict[str, float] = Field(..., description="Amount of assets per each coin.")
    ratio_per_coins: Dict[str, float] = Field(..., description="Percentage distribution of the portfolio.")
    last_rotated_at: int = Field(..., description="Unix timestamp of the last rotation performed.")
    initial_fiat_amount: float = Field(..., description="Initial amount of fiat money (USD for now) of the simulation.")
    timespan_in_hours: int = Field(..., description="Time interval in hours to perform portfolio rotation.")
    operational_fee_percentage: float = Field(..., description="Percentage of commission per operation charged by the exchange.")

class SimulationMessagesResponse(BaseModel):
    msgs: list[MessageSent] = Field(..., description="List of messages sent from the simulation.")


class SimulationCreate(BaseModel):
    initial_fiat_amount: float = Field(
        ..., ge=100, description="Initial amount of fiat money (USD for now) to start the simulation."
    )
    timespan_in_hours: int = Field(
        ..., ge=6, le=48, description="Time interval in hours to perform portfolio rotation."
    )
    trader_pro: bool = Field(
        False, description="If True, disables automatic loss protection mechanisms."
    )
    operational_fee_percentage: float = Field(
        ..., ge=0, le=1, description="Percentage of commission per operation charged by the exchange."
    )
    webhook_endpoint: str = Field(
        ...,
        description="URL to receive real-time updates about the simulation.",
        pattern=r"^https?:\/\/(?:www\.)?([-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b|localhost|(?:\d{1,3}\.){3}\d{1,3})(?::\d+)?(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)$"
    )


    model_config = {
        "json_schema_extra": {
            "example": {
                "initial_fiat_amount": 1000.0,
                "timespan_in_hours": 4,
                "trader_pro": False,
                "operational_fee_percentage": 0.1,
                "webhook_endpoint": "https://yourdomain.com/webhook"
            }
        }
    }