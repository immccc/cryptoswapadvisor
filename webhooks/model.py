from pydantic import BaseModel


class MessageSent(BaseModel):
    id: str
    msg_type: str
    content: dict
    timestamp: int