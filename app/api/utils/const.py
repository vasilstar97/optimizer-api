import os

API_TITLE = 'Optimizer API'
API_DESCRIPTION = 'API for solving project territory optimization problems'

if 'DATA_PATH' in os.environ:
    DATA_PATH = os.path.abspath(os.environ['DATA_PATH'])
else:
    raise Exception('Cannot find DATA_PATH in env')

if "URBAN_API" in os.environ:
    URBAN_API = os.environ['URBAN_API']
else:
    raise Exception('Cannot find URBAN_API in env')

DEFAULT_CRS = 4326