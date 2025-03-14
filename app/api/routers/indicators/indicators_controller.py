import json
from fastapi import APIRouter, Depends
import geopandas as gpd
from ...utils import const
from . import indicators_service

router = APIRouter(prefix='/indicators', tags=['Indicators'])

@router.post('/indicators')
def predict(
        scenario_id : int,
    ) -> dict[str, 'float']:
    result = indicators_service.predict_indicators(scenario_id)
    return result