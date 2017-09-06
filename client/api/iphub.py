import requests
import json

API_ENDPOINT = 'http://v2.api.iphub.info/ip/'

class IPHubAPI(object):
    def __init__(self, api_key):
        self.api_key = api_key
        
    @property
    def available(self):
        return True if self.api_key else False
        
    def request(self, ip):
        headers = {
            'X-Key': self.api_key
        }
        url = '{}{}'.format(API_ENDPOINT, ip)
        response = requests.get(
                url,
                headers=headers
            ).json()
        
        return response
