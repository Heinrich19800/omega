import time
import threading

MODULE_NAME = 'ChatCommands'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_chatcommands'

PERMISSION_LEVEL_VALUES = {
    'player': 0,
    'vip': 1, #TODO: VIP state still relevant?
    'support': 1,
    'moderator': 2,
    'admin': 3,
    'cftools_staff': 4
}

DEFAULT_CONFIG = {
    'command_prefix': '!',
    'commands': {
        'cftools': { #TODO: remove when finished
            'command': 'test',
            'action': 'send_formatted_message',
            'action_params': {
                'message': 'CFTools staff member {NAME} is online!',
                'target': 'all'
            },
            'required_permission_level': 'cftools_staff'
        },
        'kick': {
            'command': 'kick',
            'action': 'kick_player',
            'action_params': {
                'default_reason': 'Admin Kick'
            },
            'required_permission_level': 'support'
        }
    }
}

class ChatCommands(object):
    def __init__(self, worker):
        self.config = DEFAULT_CONFIG
        self._worker = worker
        
        config = self._worker.get_module_config(MODULE_CONFIG_ID)
        if config:
            self.config = config
            
        self._register_callbacks()
        
    def _register_callbacks(self):
        self._worker.register_callback('player', 'chat', self.incoming_chat)
        
    def incoming_chat(self, chat):
        player = chat.get('player')
        chat = chat.get('message_data')
        message = chat.get('message')
        if message[0] == self.config.get('command_prefix'):
            message = message.split()
            command = message[0].replace(self.config.get('command_prefix'), '')
            params = message[1:]
            command_data = self.validate_command(command)
            if command_data:
                return self._process_command(player, command_data, params)
            
            else:
                return player.say('Unknown command "{}"'.format(command))
                
        else: #TODO: cloud chatlogs
            pass
            
    def validate_command(self, command):
        for cmd, data in self.config.get('commands').iteritems():
            if command == cmd:
                return data
                
        return False
        
    def _replace_variables(self, message, player):
        message = message.replace('{NAME}', player.name)
        message = message.replace('{IP}',   player.ip)
        message = message.replace('{GUID}', player.guid)
        message = message.replace('{SLOT}', player.slot)
        message = message.replace('{COUNTRY}', player.country_name)
        return message
        
    def _process_command(self, player, command, params):
        player_level = PERMISSION_LEVEL_VALUES.get(player.permission_level)
        command_level = PERMISSION_LEVEL_VALUES.get(command.get('required_permission_level'))
        if player_level < command_level:
            return player.say('Unauthorized! You need to be a member of the permission group "{}" or higher to use this command'.format(command.get('required_permission_level')))
            
        if command.get('action') == 'send_basic_message':
            message = command.get('action_params').get('message')
            if command.get('action_params').get('target') == 'player':
                player.say(message)
                
            elif command.get('action_params').get('target') == 'all':
                self._worker._rcon.say_all(message)
            
        elif command.get('action') == 'send_formatted_message':
            message = command.get('action_params').get('message')
            message = self._replace_variables(message, player)
            if command.get('action_params').get('target') == 'player':
                player.say(message)
                
            elif command.get('action_params').get('target') == 'all':
                self._worker._rcon.say_all(message) 

        elif command.get('action') == 'kick_player':
            if len(params) > 0:
                player_name = params[0]
                search_result = self._worker.find_player_by_name(player_name)
                result_count = len(search_result)
                if result_count == 0:
                    player.say('No player found using "{}" as search criteria'.format(player_name))
                    
                elif result_count > 1:
                    player.say('{} players found using "{}" as search criteria. Please refine your search criteria'.format(result_count, player_name))
                    
                else:
                    target_player = search_result[0]
                    reason = ' '.join(params[1:]) if len(params[1:]) > 0 else command.get('action_params').get('default_reason')
                    target_player.kick(reason)
                    
                    player.say('Player "{}" has been kicked'.format(target_player.name))
                
                    
            else:
                player.say('!{} Syntax: !{} [name] (reason)'.format(command.get('command'), command.get('command')))
            
def hook():
    return [MODULE_NAME, MODULE_AUTHOR, ChatCommands]
