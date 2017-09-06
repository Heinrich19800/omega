import requests
import hashlib
from time import time

DEFAULT_HEADERS = {
    'User-Agent': 'CFTools-Omega-Client',
}

class CFToolsAPI(object):
    def __init__(self, identity, key, application, error_mode=0, refresh_auth=True, headers={}, host='cfbackend.de', protocol='https'):
        self.host = host
        self.protocol = protocol
        
        self.identity = identity
        self.key = key
        self.access_token = ''
        
        self.application = application
        
        self.error_mode = error_mode
        self.refresh_auth = refresh_auth
        
        self.headers = DEFAULT_HEADERS
        self.headers.update(headers)
        
    @property
    def secured_key(self):
        timestamp = time()
        h = hashlib.sha512()
        h.update(str(timestamp))
        h.update(self.key)
        return [timestamp, h.hexdigest()]
        
    @property
    def url(self):
        return '{}://{}'.format(self.protocol, self.host)
        
    @property
    def app_url(self):
        return '{}/{}'.format(self.url, self.application)
        
    def _build_app_url(self, *args):
        url = '{}/{}'.format(
            self.app_url,
            '/'.join(args)
        )
        return url
        
    def _build_url(self, *args):
        url = '{}/{}'.format(
            self.url,
            '/'.join(args)
        )
        return url
        
    def app_request(self, payload = {}, *args, **kwargs):
        url = self._build_app_url(*args)
        stream = True if 'stream' in kwargs and kwargs.get('stream') else False
        return self._request(payload, url, stream)
        
    def direct_request(self, payload, *args):
        url = self._build_url(*args)
        return self._request(payload, url)
        
    def _request(self, payload, url, stream=False):
        headers = self.headers
        headers.update({
            'Authorization': 'Bearer {}'.format(self.access_token), 
            'CF-API-Identity': self.identity
        })

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=stream
            ).json()
        
        except requests.exceptions.ConnectionError as e:
            return self._exception(Exception, 'Cant reach CFTools master server')

        if not response.get('success') and response.get('error_message') == 'expired token':
            self.register()
            return self._request(payload, url)
            
        return response
        
    def _exception(self, exception, message):
        msg = '{}: {}'.format(exception, message)
        if self.error_mode == 0:
            raise exception(msg)
            
        elif self.error_mode == 1:
            print '\n----------------------------------------------------------'
            print '[CFToolsAPI-Exception] {}'.format(msg)
            print '----------------------------------------------------------'
        
        return {
            'success': False,
            'error_message': msg
        }
        
    def register(self):
        secured = self.secured_key
        auth_data = {
            'key': secured[1],
            'client_time': secured[0],
            'application': self.application
        }
        response = self.direct_request(auth_data, 'register')

        if response.get('success'):
            self.access_token = response.get('access_token')
            return response
            
        else:
            return self._exception(Exception, 'invalid access_token')

    def verify_access_token(self):
        response = self.direct_request({}, 'whoami')
        if response.get('success'):
            return response
        
        else:
            return self._exception(Exception, 'cant verify access_token')
        
    def retrieve_service_status(self):
        response = self.direct_request({}, 'status')
        
        status = response.get('status')
        return status
