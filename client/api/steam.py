import requests
import xml.etree.ElementTree as ET

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

    def retrieve_group_members(self, group_id):
        members = []
        url = 'http://steamcommunity.com/gid/{}/memberslistxml/?xml=1'.format(group_id)
        response = requests.get(url)
        data = ET.XML(response.text)
        for member in data.findall('members'):
            for node in member.getiterator():
                if node.tag == 'steamID64':
                    members.append(node.text)

        return members
        