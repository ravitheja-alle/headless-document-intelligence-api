from pydantic import BaseModel, Field
from typing import List

class ExtractionRequest(BaseModel):
    fields: List[str] = Field(..., example=["total_amount", "vendor_name", "invoice_date"])
    mock: bool = Field(default=True,description="Use mock extraction mode")