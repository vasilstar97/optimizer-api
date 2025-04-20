import requests
import pandas as pd
import geopandas as gpd
from fastapi import HTTPException
from .const import URBAN_API, DEFAULT_CRS

def _raise_for_status(response : requests.Response):
    try:
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(response.status_code, detail=str(e))

def _headers_from_token(token : str | None):
    headers = {}
    if token is not None:
        headers['Authorization'] = f'Bearer {token}'
    return headers

def get_scenario_by_id(scenario_id : int, token : str | None):
    res = requests.get(URBAN_API + f'/api/v1/scenarios/{scenario_id}', headers=_headers_from_token(token))
    _raise_for_status(res)
    return res.json()

def get_project_by_id(project_id : int, token : str | None):
    res = requests.get(URBAN_API + f'/api/v1/projects/{project_id}/territory', headers=_headers_from_token(token))
    _raise_for_status(res)
    return res.json()

def get_functional_zones_sources(scenario_id : int, token : str | None):
    res = requests.get(f'{URBAN_API}/api/v1/scenarios/{scenario_id}/functional_zone_sources', headers=_headers_from_token(token))
    _raise_for_status(res)
    return pd.DataFrame(res.json())

def get_functional_zones(scenario_id : int, year : int, source : str, token : str | None):
    res = requests.get(f'{URBAN_API}/api/v1/scenarios/{scenario_id}/functional_zones', params={
        'year': year,
        'source': source
    }, headers=_headers_from_token(token))
    _raise_for_status(res)
    return gpd.GeoDataFrame.from_features(res.json()['features'], crs=DEFAULT_CRS)

def get_functional_zones_types():
    res = requests.get(f'{URBAN_API}/api/v1/functional_zones_types')
    _raise_for_status(res)
    res_json = res.json()
    return pd.DataFrame(res_json).set_index('functional_zone_type_id')
