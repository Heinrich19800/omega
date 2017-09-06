import requests


class SteamAPI(object):
    def __init__(self, steam_api_key):
        self.api_key = steam_api_key
        
    @property
    def available(self):
        return True if self.api_key else False
        
    def profile(self, steamid):
        url = 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0001/?key={}&steamids={}'.format(self.api_key, steamid)
        response = requests.get(url).json()
        return response['response']['players']['player'][0] or {}
