import requests
import json

API_PROVIDER    = 'http://freegeoip.net'
ENDPOINT        = '/json/'

DEBUG_LOCATION_DATA = {
    'city': '', 
    'region_code': '', 
    'region_name': '', 
    'ip': '127.0.0.1', 
    'time_zone': '', 
    'longitude': 0, 
    'metro_code': 0, 
    'latitude': 0, 
    'country_code': '', 
    'country_name': '', 
    'zip_code': ''
}

class OmegaLocation(object):
    ip = ''
    
    error = False
    error_message = ''
    
    _location_data = { }
    
    def __init__(self, ip):
        self.ip = ip
        self._fetch_data()
        
    def __getattr__(self, key):
        if key not in self._location_data.keys():
            raise AttributeError('No attribute "%s" '.format(repr(key)))
        return self._location_data.get(key)
        
    def _fetch_data(self):
        uri = '{}{}{}'.format(API_PROVIDER, ENDPOINT, self.ip)
        try:
            response = requests.get(uri)
            self._location_data = response.json()
            
        except Exception as e:
            self._location_data = DEBUG_LOCATION_DATA
            self.error = True
            self.error_message = response.text
