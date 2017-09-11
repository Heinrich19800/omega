import requests

def resolve_ip(ip):
    url = 'https://cfbackend.de/ip/{}'.format(ip)
    response = requests.get(url).json()
    return response