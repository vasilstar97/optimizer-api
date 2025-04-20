import json
from fastapi import APIRouter, Depends
import geopandas as gpd
from ...utils import const, auth
from . import indicators_service

router = APIRouter(prefix='/indicators', tags=['Indicators'])

@router.post('/predict')
def predict(
        scenario_id : int, token : str | None = Depends(auth.verify_token)
    ) -> dict[str, 'float']:
    result = indicators_service.predict_indicators(scenario_id, token)
    return result