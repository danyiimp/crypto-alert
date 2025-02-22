from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaseTokenResponse(BaseModel):
    symbol: str


class PairRepsonse(BaseModel):
    price_usd: float = Field(alias="priceUsd")
    base_token: BaseTokenResponse = Field(alias="baseToken")


class TokenStatusResponse(BaseModel):
    pairs: list[PairRepsonse]


class Subscription(BaseModel):
    chain_id: str
    token_name: str
    token_address: str
    price: float
    alert_price: float | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    def __str__(self) -> str:
        if self.alert_price is None:
            raise ValueError(
                "String representation is not available until alert_price is set"
            )

        return (
            f"{self.token_name} ({self.chain_id.upper()}):\n"
            f"Address: {self.token_address}\n"
            f"Price: {self.price} USD\n"
            f"Alert Price: {self.alert_price} USD\n"
            f"Last Updated: {self.updated_at.strftime('%d-%m-%Y %H:%M:%S')} UTC"
        )
