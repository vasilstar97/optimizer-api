import json
import geopandas as gpd
from functools import wraps
from shapely import set_precision
from .const import DEFAULT_CRS

# PRECISION_GRID_SIZE = 0.00001

def gdf_to_geojson(func):
    """
    A decorator that processes a GeoDataFrame returned by an asynchronous function and converts it to GeoJSON format with specified CRS and geometry precision.

    This decorator takes an asynchronous function that returns a GeoDataFrame, transforms its coordinate system to EPSG:4326, 
    and optionally adjusts the geometry precision based on a defined grid size. The final result is a GeoJSON-compatible dictionary.

    Parameters
    ----------
    func : Callable
        An asynchronous function that returns a GeoDataFrame.

    Returns
    -------
    Callable
        A wrapped asynchronous function that returns the GeoDataFrame as a GeoJSON-compatible dictionary.

    Notes
    -----
    - The decorator converts the GeoDataFrame to EPSG:4326 (WGS 84).
    - Geometry precision is adjusted using the `set_precision` function and a grid size defined by `PRECISION_GRID_SIZE`.
    - Commented-out code allows optional rounding for columns containing 'provision' in their name, if enabled.
    
    Examples
    --------
    ```
    @gdf_to_geojson
    async def get_geodata():
        # returns a GeoDataFrame
        return gdf
    ```
    """
    @wraps(func)
    def process(*args, **kwargs):
        gdf = func(*args, **kwargs).to_crs(DEFAULT_CRS)
        # gdf.geometry = set_precision(gdf.geometry, grid_size=PRECISION_GRID_SIZE)
        return json.loads(gdf.to_json())
    return process