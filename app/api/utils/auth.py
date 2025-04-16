from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

http_bearer = HTTPBearer(auto_error=False)

def _get_token_from_header(credentials: HTTPAuthorizationCredentials) -> str:

    if credentials is None:
        return None

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token is missing in the authorization header"
        )
    
    return token

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):
    return _get_token_from_header(credentials)
