from fastapi import APIRouter

router = APIRouter(prefix='/my_router', tags=['My router'])

@router.get('/my_endpoint')
def get_my_endpoint(a : int, b : int) -> int:
  return a + b