import os

API_TITLE = 'Optimizer API'
API_DESCRIPTION = 'API for solving project territory optimization problems'
DATA_PATH = os.path.abspath('app/data')
if "URBAN_API" in os.environ:
    URBAN_API = os.environ['URBAN_API']
else:
    raise Exception('Cannot find URBAN_API in env')
DEFAULT_CRS = 4326