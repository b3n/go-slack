from datetime import datetime
from pickle import dump, load
from sys import argv
from time import sleep, time
import random
import re

from slackclient import SlackClient
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
        self.id = self.get_id()
        self.goban = self.load_goban()
        self.resign_requested = False

    def get_id(self) -> str:
        # TODO: There has to be a better way of doing this...
        members = self.slack_client.api_call('users.list')['members']
        for member in members:
            if member['name'] == config.USERNAME:
                return member['id']

    def start(self) -> None:
        if self.slack_client.rtm_connect():
            try:
                while True:
                    for event in self.slack_client.rtm_read():
                        private_message = event.get('channel', [None])[0] == 'D'
                        if (event.get('type') == 'message' and event.get('text') and
                        ('<@{id}>'.format(id=self.id) in event.get('text') or private_message)):
                            self.process_message(event['text'], event['channel'], event['user'], private_message)
                        if config.DEBUG:
                            print(event)
                    self.run_cron()
                    self.ping()
                    sleep(0.2) # Raise this for slower responses but less CPU use.

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

    def process_message(self, message: str, channel: str, user: str, private_message: bool) -> None:
        move = None
        result = None

        if self.vocab_in_message('VOTE', message):
            move = re.search(Move.MOVE_PATTERN, message)
        if move:
            result = self.goban.vote_move(Move(move.group(0), private_message), user)
        elif self.vocab_in_message('VOTES', message):
            result = self.goban.get_votes()
        elif self.vocab_in_message('CAPTURES', message):
            result = self.goban.get_captures()
        elif self.vocab_in_message('SHOW', message):
            result = self.goban.show_board()
        elif self.vocab_in_message('PASS', message):
            result = self.goban.pass_move()
        elif self.vocab_in_message('RANDOM', message):
            result = self.goban.vote_random(user, private_message)
        elif self.vocab_in_message('YES', message) and self.resign_requested:
            self.resign_requested = False
            result = self.goban.resign()
        elif self.vocab_in_message('NO', message) and self.resign_requested:
            self.resign_requested = False
            result = random.choice(config.RESPONSES['RESIGN_CONFIRMATION'])
        elif self.vocab_in_message('RESIGN', message):
            self.resign_requested = True
            result = random.choice(config.RESPONSES['RESIGN_CONFIRMATION'])
        else:
            result = random.choice(config.RESPONSES['UNKNOWN'])

        self.slack_client.rtm_send_message(channel, result)

        if private_message and ('Voted' in result or 'Changed' in result):  # TODO: This is hacky.
            # Send a public announcement.
            user_info = self.slack_client.api_call('users.info', user=user)['user']
            message = '@{} {}'.format(user_info['name'], result)
            self.slack_client.rtm_send_message(config.CHANNEL, message)

    def vocab_in_message(self, command: str, message: str) -> bool:
        pattern = re.compile(r'\b({})\b'.format('|'.join(config.VOCAB[command])), re.IGNORECASE)
        return pattern.search(message)

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
