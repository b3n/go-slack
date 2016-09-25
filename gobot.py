from datetime import datetime
from pickle import dump, load
from slackclient import SlackClient
from sys import argv
from time import sleep, time
from websocket import WebSocketConnectionClosedException
import pycron

import config
from goban import Goban, Move


class GoBot:
    STATE_FILE_NAME = 'goban.pkl'

    def __init__(self, token: str) -> None:
        self.slack_client = SlackClient(token)
        self.ran_cron = False
        self.last_ping = 0
        self.goban = self.load_goban()

    def start(self) -> None:
        if self.slack_client.rtm_connect():
            try:
                while True:
                    for event in self.slack_client.rtm_read():
                        if 'type' in event and event['type'] == 'message' and 'text' in event and event['text'][0] == '!':
                            private_message = event['channel'][0] == 'D'
                            self.process_command(event['text'], event['channel'], event['user'], private_message)

                        if config.DEBUG:
                            print(event)

                    self.run_cron()
                    self.ping()
                    sleep(0.1)

            # There seems to be a bug with `slackclient==1.0.0` (github.com/slackhq/python-slackclient/issues/118), so
            # for now if the connection dies like this let's just start it up again.
            except WebSocketConnectionClosedException:
                if config.DEBUG:
                    print('Restarting connection.')
                self.start()

        else:
            print('Connection Failed. Invalid token?')

    def ping(self) -> None:
        now = time()
        if now > self.last_ping + 3:
            self.slack_client.server.ping()
            self.last_ping = now

    def process_command(self, text: str, channel: str, user: str, private_message: bool) -> None:
        words = text.split()
        command = words[0][1:].lower()
        arguments = words[1:]

        if command == 'vote':
            if len(arguments) > 0:
                result = self.goban.vote_move(Move(arguments[0], private_message), user)
            else:
                result = "You need to type a move, e.g. `!vote J10`. I'm just a humble bot, not a mind reader."
        elif command == 'votes':
            result = self.goban.get_votes()
        elif command == 'captures':
            result = self.goban.get_captures()
        elif command == 'show':
            result = self.goban.show_board()
        else:
            result = 'Invalid command, try: `!vote`, `!votes`, `!show`, `!captures`.'

        self.slack_client.rtm_send_message(channel, result)

        if private_message and ('Voted' in result or 'Changed' in result):  # TODO: This is hacky.
            # Send a public announcement.
            user_info = self.slack_client.api_call('users.info', user=user)['user']
            message = '@{} {}'.format(user_info['name'], result)
            self.slack_client.rtm_send_message(config.CHANNEL, message)

    def run_cron(self) -> None:
        should_run = pycron.is_now(config.CRON)
        if not self.ran_cron and should_run:
            self.ran_cron = True
            result = self.goban.play_move()
            if result:
                self.slack_client.rtm_send_message(config.CHANNEL, result)
                self.save_goban()

        elif not should_run:
            self.ran_cron = False

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
