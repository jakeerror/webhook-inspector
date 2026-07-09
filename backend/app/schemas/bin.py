from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    expires_at: datetime
    request_count: int


class BinCreateResponse(BinRead):
    url: str
