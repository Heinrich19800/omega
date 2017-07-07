import time
import threading

MODULE_NAME = 'ChatCommands'
MODULE_AUTHOR = 'philippj'
MODULE_CONFIG_ID = 'official_chatcommands'

DEFAULT_CONFIG = {
    'command_prefix': '!',
    'commands': {
        'test': {
            'command': 'test',
            'action': 'send_basic_message',
            'action_params': {
                'message': 'test command executed successfully',
                'target': 'player'
            }
        },
        'kick': {
            'command': 'kick',
            'action': 'kick_player',
            'action_params': {
                'default_reason': 'Admin Kick'
            }
        }
    }
}

class ChatCommands(object):
    config = DEFAULT_CONFIG
    _worker = None
    
    def __init__(self, worker):
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
            command = self.validate_command(command)
            if command:
                return self._process_command(player, command, params)
            
            else:
                return player.say('Unknown command "{}"', command)
                
        else: #implement cloud based chatlogs
            pass
            #logging moved to console_logging module
            
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
        if command.get('action') == 'send_basic_message':
            message = command.get('action_params').get('message')
            if command.get('action_params').get('target') == 'player':
                player.say(message)
                
            elif command.get('action_params').get('target') == 'all':
                self._worker._rcon.say_all(message)
            
        elif command.get('action') == 'send_formatted_message':
            message = command.get('action_params').get('message')
            message = self._replace_variables(message, player)
            player.say(message)
                
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
            
            
        #message = '{} issued {} with params {}'.format(player.name, command, params)
        #player.say(message)
    
def hook():
    return [MODULE_NAME, MODULE_AUTHOR, ChatCommands]