from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

oauth2_scheme = APIKeyHeader(name="Authorization")

def _get_token_from_header(header : str) -> str:
    if not header:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
        )
    # Проверяем формат: заголовок должен начинаться с 'Bearer '
    if not header.startswith("Bearer "):
        raise HTTPException(
            status_code=400,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )
    
    token = header[len("Bearer "):]

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token is missing in the authorization header"
        )
    
    return token

async def verify_token(header: str = Depends(oauth2_scheme)):
    token = _get_token_from_header(header)
    return token