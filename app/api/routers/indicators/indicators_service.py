import json
import pandas as pd
import geopandas as gpd
import shapely
import requests
from .indicators import get_indicators
from ...utils.const import URBAN_API

def get_functional_zones_sources(scenario_id : int):
    res = requests.get(f'{URBAN_API}/api/v1/scenarios/{scenario_id}/functional_zone_sources')
    return pd.DataFrame(res.json())

def get_best_source(df : pd.DataFrame):
    sources = df['source'].unique()
    if len(sources) == 0:
        return None
    for s in ['OSM', 'PZZ', 'User']:
        if s in sources:
            source = s
    df = df[df['source'] == source].sort_values('year', ascending=False)
    return df.iloc[0]

def get_functional_zones(scenario_id : int, year : int, source : str):
    res = requests.get(f'{URBAN_API}/api/v1/scenarios/{scenario_id}/functional_zones', params={
        'year': year,
        'source': source
    })
    gdf = gpd.GeoDataFrame.from_features(res.json()['features'], crs=4326)
    for key in ['id', 'name']:
        gdf[f'functional_zone_type_{key}'] = gdf['functional_zone_type'].apply(lambda fzt : fzt[key])
    crs = gdf.estimate_utm_crs()
    return gdf.to_crs(crs)

def get_scenario_by_id(scenario_id : int):
    res = requests.get(URBAN_API + f'/api/v1/scenarios/{scenario_id}')
    return res.json()

def get_project_by_id(project_id : int):
    res = requests.get(URBAN_API + f'/api/v1/projects/{project_id}/territory')
    return res.json()

def get_scenario_geometry(scenario_id : int):
    project_id = get_scenario_by_id(scenario_id)['project']['project_id']
    project_info = get_project_by_id(project_id)
    geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(geometry_json)

def predict_indicators(scenario_id : int):
    sources = get_functional_zones_sources(scenario_id)
    source = get_best_source(sources)
    functional_zones = get_functional_zones(scenario_id, **source)
    
    scenario_geom = get_scenario_geometry(scenario_id)
    scenario_gdf = gpd.GeoDataFrame(geometry=[scenario_geom], crs=4326).to_crs(functional_zones.crs)
    scenario_area = scenario_gdf.area.sum()

    indicators = get_indicators(functional_zones, 'functional_zone_type_name', None, scenario_area)

    return {**indicators}