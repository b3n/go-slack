from time import sleep, time
from datetime import datetime
from sys import argv
from pickle import dump, load
from slackclient import SlackClient

import config
from goban import Goban


class GoBot:
    STATE_FILE_NAME = 'goban.pkl'

    def __init__(self, token: str) -> None:
        self.slack_client = SlackClient(token)
        self.last_ran_crons = 0
        self.last_ping = 0
        self.channels = []
        self.goban = self.load_goban()

    def start(self) -> None:
        if self.slack_client.rtm_connect():
            all_channels = self.slack_client.api_call('channels.list')['channels']
            self.channels = [channel['id'] for channel in all_channels if channel['is_member']]
            while True:
                for event in self.slack_client.rtm_read():
                    if 'type' in event and event['type'] == 'message' and 'text' in event and event['text'][0] == '!':
                        self.process_command(event['text'], event['channel'], event['user'])

                    if config.DEBUG:
                        print(event)

                self.hourly_crons()
                self.ping()
                sleep(0.1)
        else:
            print('Connection Failed, invalid token?')

    def ping(self) -> None:
        now = time()
        if now > self.last_ping + 3:
            self.slack_client.server.ping()
            self.last_ping = now

    def process_command(self, text: str, channel: str, user: str) -> None:
        words = text.split()
        command = words[0][1:].lower()
        arguments = words[1:]

        if command == 'vote':
            if len(arguments) > 0:
                result = self.goban.vote_move(arguments[0], user)
            else:
                result = "You need to type a move, e.g. `!vote J10`. I'm just a humble bot, not a mind reader."
        elif command == 'votes':
            result = self.goban.get_votes()
        elif command == 'captures':
            result = self.goban.get_captures()
        elif command == 'show':
            result = self.goban.show_board()
        else:
            result = 'Invalid command, try: `!vote`, `!votes`, `!show`.'

        self.slack_client.rtm_send_message(channel, result)

    def hourly_crons(self) -> None:
        now = time()

        if config.DEBUG:
            run_cron = now >= self.last_ran_crons + 10
        else:
            run_cron = now >= self.last_ran_crons + 60 * 60 and datetime.now().minute == 0

        if run_cron:
            result = self.goban.play_move()
            if result:
                self.slack_client.rtm_send_message(self.channels[0], result)
                self.save_goban()

            self.last_ran_crons = now

    def save_goban(self) -> None:
        with open(self.STATE_FILE_NAME, 'wb') as file:
            dump(self.goban, file)

    def load_goban(self) -> Goban:
        try:
            with open(self.STATE_FILE_NAME, 'rb') as file:
                return load(file)
        except FileNotFoundError:
            return Goban()


if __name__ == '__main__':
    if len(argv) < 2:
        print('Please provide a Slack token as the argument.')
    else:
        bot = GoBot(argv[1])
        bot.start()
