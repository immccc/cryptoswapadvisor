from pydantic import BaseModel, Field


class UserPatch(BaseModel):
    webhook_link: str = Field(
        ..., description="User webhook link"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "webhook_link": "http://www.myaddress.com/webhook"
            }
        }
    }