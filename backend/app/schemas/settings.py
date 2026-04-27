from pydantic import BaseModel, Field


class LinkedInCredentialsRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LinkedInStatusResponse(BaseModel):
    has_credentials: bool
    email: str | None = None
    last_scraped_at: str | None = None
