import geopandas as gpd
from fastapi import APIRouter
from ...utils import decorators

router = APIRouter(prefix='/network', tags=['Network'])

@router.post('/generate')
@decorators.gdf_to_geojson
def generate():
    ...