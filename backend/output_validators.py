"""
Utilities for structured LLM output parsing and validation.
"""

import json
import logging
from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


def parse_json_response(response_text: str, schema: Type[T], fallback: Any = None) -> T:
    """
    Parse LLM response as JSON and validate against Pydantic schema.
    
    Args:
        response_text: Raw response from LLM
        schema: Pydantic model to validate against
        fallback: Fallback value if parsing fails
    
    Returns:
        Validated Pydantic model instance or fallback
    
    Raises:
        ValidationError if schema validation fails and no fallback provided
    """
    try:
        # Extract JSON from response (handles cases where LLM returns extra text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning("No JSON object found in LLM response")
            if fallback is not None:
                return fallback
            raise ValueError("No JSON found in response")
        
        json_str = response_text[json_start:json_end]
        data = json.loads(json_str)
        
        return schema(**data)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        if fallback is not None:
            return fallback
        raise
    
    except ValidationError as e:
        logger.error(f"Schema validation error: {e}")
        if fallback is not None:
            return fallback
        raise


def escape_json_string(text: str) -> str:
    """Escape text for safe JSON embedding."""
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')


def create_json_prompt(schema: Type[BaseModel], instructions: str = "") -> str:
    """
    Create a prompt instructing LLM to output JSON matching a schema.
    
    Args:
        schema: Pydantic model defining output structure
        instructions: Additional instructions for the LLM
    
    Returns:
        Formatted prompt text
    """
    schema_example = schema.model_json_schema()
    
    prompt_parts = [
        "You MUST respond with valid JSON only, no other text.",
        "",
        f"Expected JSON Schema:\n{json.dumps(schema_example, indent=2)}",
        ""
    ]
    
    if instructions:
        prompt_parts.insert(2, instructions)
        prompt_parts.insert(3, "")
    
    return "\n".join(prompt_parts)


def validate_and_repair(json_str: str, schema: Type[T], repair_attempts: int = 2) -> T:
    """
    Attempt to parse and repair malformed JSON responses.
    
    Args:
        json_str: Potentially malformed JSON string
        schema: Pydantic model to validate against
        repair_attempts: Number of repair attempts
    
    Returns:
        Validated instance or raises error
    """
    # Try direct parse first
    try:
        data = json.loads(json_str)
        return schema(**data)
    except (json.JSONDecodeError, ValidationError):
        pass
    
    # Repair attempts
    for attempt in range(repair_attempts):
        try:
            # Common fixes: missing closing brace, trailing comma, etc.
            repaired = json_str.rstrip()
            if not repaired.endswith('}'):
                repaired += '}'
            
            # Remove trailing commas in objects
            repaired = repaired.replace(',}', '}')
            repaired = repaired.replace(',]', ']')
            
            data = json.loads(repaired)
            return schema(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.debug(f"Repair attempt {attempt + 1} failed: {e}")
    
    raise ValueError(f"Could not parse or repair JSON after {repair_attempts} attempts")
