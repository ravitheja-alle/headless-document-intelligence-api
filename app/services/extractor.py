import logging
from typing import List, Dict, Any, Type
from pydantic import BaseModel, create_model
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# SAFE CLIENT INITIALIZATION
client = None

if settings.OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def generate_dynamic_schema(fields: List[str]) -> Type[BaseModel]:
    """
    Dynamically constructs a Pydantic model from a list of string fields.
    Forces the LLM to return a string for every requested field.
    """
    # Define each field as a required string. 
    field_definitions = {field: (str, ...) for field in fields}
    return create_model('DynamicExtractionSchema', **field_definitions)

async def extract_data(text: str, fields: List[str], mock: bool = False) -> Dict[str, Any]:
    """
    Executes the extraction against OpenAI using Structured Outputs.
    """
    if not mock and client is None:
        raise Exception("OpenAI client not configured.")

    if mock:
        return {field: f"mock_{field}_value" for field in fields}

    DynamicSchema = generate_dynamic_schema(fields)
    
    system_prompt = (
        "You are a precise data extraction engine. Extract the requested fields from the provided document text. "
        "If a field is not explicitly found in the text, output 'NOT FOUND' as the value. Do not invent data."
    )

    try:
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format=DynamicSchema,
        )
        # Parse the strictly typed response into a dictionary
        return response.choices[0].message.parsed.model_dump()
    except Exception as e:
        logger.error(f"OpenAI Extraction Error: {str(e)}")
        raise