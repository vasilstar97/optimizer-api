import json
import pandas as pd
import geopandas as gpd
import shapely
from loguru import logger
from .indicators import get_indicators
from ...utils import api_client, const

def _get_best_source(df : pd.DataFrame):
    sources = df['source'].unique()
    if len(sources) == 0:
        return None
    for s in ['OSM', 'PZZ', 'User']:
        if s in sources:
            source = s
    df = df[df['source'] == source].sort_values('year', ascending=False)
    return df.iloc[0]

def _get_functional_zones(scenario_id : int, token : str | None) -> gpd.GeoDataFrame:
    logger.info('Getting functional zones')
    sources = api_client.get_functional_zones_sources(scenario_id, token)
    source = _get_best_source(sources)
    gdf = api_client.get_functional_zones(scenario_id, token=token, **source)
    for key in ['id', 'name']:
        gdf[f'functional_zone_type_{key}'] = gdf['functional_zone_type'].apply(lambda fzt : fzt[key])
    crs = gdf.estimate_utm_crs()
    return gdf.to_crs(crs)

def _get_scenario_geometry(scenario_id : int, token):
    project_id = api_client.get_scenario_by_id(scenario_id, token)['project']['project_id']
    project_info = api_client.get_project_by_id(project_id, token)
    geometry_json = json.dumps(project_info['geometry'])
    return shapely.from_geojson(geometry_json)

def predict_indicators(scenario_id : int, token : str | None):
    functional_zones = _get_functional_zones(scenario_id, token)
    scenario_geom = _get_scenario_geometry(scenario_id, token)

    scenario_gdf = gpd.GeoDataFrame(geometry=[scenario_geom], crs=const.DEFAULT_CRS).to_crs(functional_zones.crs)
    scenario_area = scenario_gdf.area.sum()

    indicators = get_indicators(functional_zones, 'functional_zone_type_name', None, scenario_area)

    return {**indicators}