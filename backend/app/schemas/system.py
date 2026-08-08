from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class VersionResponse(BaseModel):
    version: str
    layer1_model: str 
