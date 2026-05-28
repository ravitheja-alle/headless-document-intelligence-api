from pydantic import BaseModel, Field
from typing import List

class ExtractionRequest(BaseModel):
    fields: List[str] = Field(..., example=["total_amount", "vendor_name", "invoice_date"])
    mock: bool = Field(False, description="Set to true to bypass OpenAI and return dummy data during dev.")