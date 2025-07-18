from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from src.utils.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def validate_api_key(api_key: str = Depends(api_key_header)):
    """Validate the API key against the stored key in settings."""
    if api_key != settings.API_KEY.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return True

