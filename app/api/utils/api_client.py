import requests

URBAN_API = 'https://urban-api.idu.kanootoko.org'

def get_scenario_by_id(scenario_id : int, token : str):
    res = requests.get(URBAN_API + f'/api/v1/scenarios/{scenario_id}', headers={'Authorization': f'Bearer {token}'})
    return res.json()

def get_project_by_id(project_id : int, token : str):
    res = requests.get(URBAN_API + f'/api/v1/projects/{project_id}/territory', headers={'Authorization': f'Bearer {token}'})
    return res.json()