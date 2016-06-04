from time import sleep, time
from datetime import datetime
import re
from random import choice
from sys import argv
from collections import Counter
from typing import List, Optional, Tuple

from slackclient import SlackClient
from imgurpython import ImgurClient
from PIL import Image, ImageDraw

DEBUG = True


class GoBot:
    def __init__(self, token: str) -> None:
        self.slack_client = SlackClient(token)
        self.goban = Goban()
        self.last_ran_crons = 0
        self.channels = []

    def start(self) -> None:
        if self.slack_client.rtm_connect():
            all_channels = self.slack_client.api_call('channels.list')['channels']
            self.channels = [channel['id'] for channel in all_channels if channel['is_member']]
            while True:
                for event in self.slack_client.rtm_read():
                    if 'type' in event and event['type'] == 'message' and 'text' in event and event['text'][0] == '!':
                        self.process_command(event['text'], event['channel'], event['user'])
                    print(event)

                self.hourly_crons()
                sleep(1)
        else:
            print('Connection Failed, invalid token?')

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
        elif command == 'show':
            result = self.goban.show_board()
        else:
            result = 'Invalid command, try: `!vote`, `!votes`, `!show`.'

        self.slack_client.rtm_send_message(channel, result)

    def hourly_crons(self) -> None:
        now = time()

        if DEBUG:
            run_cron = now >= self.last_ran_crons + 10
        else:
            run_cron = now >= self.last_ran_crons + 60 * 60 and datetime.now().minute == 0

        if run_cron:
            result = self.goban.play_move()
            if result:
                self.slack_client.rtm_send_message(self.channels[0], result)
            self.last_ran_crons = now


class Goban:
    Group = List[Tuple[int, int]]

    def __init__(self) -> None:
        self.votes = {}
        self.image_url = 'https://i.imgur.com/iWzRKV0.png'
        self.imgur_client = ImgurClient('6584aa67fc46a02', 'fda614da4406c63a395bd0748c1fb74adeccc5ef')
        self.move_pattern = re.compile(r'^([a-t])([1-9]|1[0-9])$', re.IGNORECASE)
        self.next_turn_color = 'black'
        self.moves = [[None] * 19 for _ in range(19)]

    def vote_move(self, move: str, user: str) -> str:
        if move.lower() == 'pass':
            return '// TODO: Implement passing and end game... :robot_face:'

        if not self.move_pattern.match(move):
            return "Oops, I don't understand `{}`, is that supposed to be somewhere on the board?".format(move)

        if not self.is_valid(move):
            return '`{}` seems to be an invalid move.'.format(move)

        if user in self.votes:
            if self.votes[user].lower() == move.lower():
                return "You've already voted for `{}`!".format(move)
            else:
                old_move = self.votes[user]
                self.votes[user] = move
                return 'Changed vote from `{}` to `{}`!'.format(old_move, move)

        self.votes[user] = move
        return 'Voted for `{}`.'.format(move)

    def is_valid(self, move_reference: str) -> bool:
        # TODO: Check if suicidal
        x, y = self.get_coordinates(move_reference)
        return self.moves[x][y] is None

    def get_votes(self) -> str:
        if len(self.votes) == 0:
            return 'No votes.'

        vote_counts = Counter(self.votes.values())
        vote_percentages = [(move, vote_counts[move] / len(self.votes)) for move in vote_counts]

        message = ''
        for move, percentage in vote_percentages:
            message += '`{}` {:.0%} chance of being played.\n'.format(move, percentage)

        return message

    def play_move(self) -> Optional[str]:
        if len(self.votes) == 0:
            return None

        move = choice(list(self.votes.values()))
        self.votes = {}

        x, y = self.get_coordinates(move)

        # Place stone
        self.moves[x][y] = self.next_turn_color
        self.next_turn_color = 'white' if self.next_turn_color == 'black' else 'black'

        # Remove captures
        if x + 1 < 19 and self.moves[x + 1][y] == self.next_turn_color:
            self.remove_if_captured(x + 1, y)
        if y + 1 < 19 and self.moves[x][y + 1] == self.next_turn_color:
            self.remove_if_captured(x, y + 1)
        if x - 1 >= 0 and self.moves[x - 1][y] == self.next_turn_color:
            self.remove_if_captured(x - 1, y)
        if y - 1 >= 0 and self.moves[x][y - 1] == self.next_turn_color:
            self.remove_if_captured(x, y - 1)

        self.draw_board()
        return 'Playing move `{}`.\n{}'.format(move, self.image_url)

    def get_coordinates(self, move_reference: str) -> (int, int):
        move_coords = self.move_pattern.match(move_reference).groups()

        x = ord(move_coords[0].upper()) - ord('A')
        y = 19 - int(move_coords[1])

        return x, y

    def remove_if_captured(self, x: int, y: int) -> None:
        group = self.build_group(x, y)
        if not self.has_liberties(group):
            for x, y in group:
                self.moves[x][y] = None

    def has_liberties(self, group: Group) -> bool:
        for x, y in group:
            if (x + 1 < 19 and self.moves[x + 1][y] is None or
                    y + 1 < 19 and self.moves[x][y + 1] is None or
                    x - 1 >= 0 and self.moves[x - 1][y] is None or
                    y - 1 >= 0 and self.moves[x][y - 1] is None):
                return True

        return False

    def build_group(self, x: int, y: int, group: Optional[Group]=None) -> Group:
        if not group:
            group = []

        if self.moves[x][y] and (x, y) not in group:
            group.append((x, y))
            if x + 1 < 19 and self.moves[x + 1][y] == self.moves[x][y]:
                group = self.build_group(x + 1, y, group)
            if y + 1 < 19 and self.moves[x][y + 1] == self.moves[x][y]:
                group = self.build_group(x, y + 1, group)
            if x - 1 >= 0 and self.moves[x - 1][y] == self.moves[x][y]:
                group = self.build_group(x - 1, y, group)
            if y - 1 >= 0 and self.moves[x][y - 1] == self.moves[x][y]:
                group = self.build_group(x, y - 1, group)

        return group

    def show_board(self) -> str:
        return self.image_url

    def draw_board(self) -> None:
        im = Image.open('goban_blank.png')

        draw = ImageDraw.Draw(im)
        for x in range(19):
            for y in range(19):
                if self.moves[x][y]:
                    draw.ellipse([(x * 20 + 10, y * 20 + 10), (x * 20 + 30, y * 20 + 30)], fill=self.moves[x][y])

        file_path = 'goban_with_moves.png'
        im.save(file_path, 'PNG')
        upload = self.imgur_client.upload_from_path(file_path)

        self.image_url = upload['link']


if __name__ == '__main__':
    if len(argv) < 2:
        print('Please provide a Slack token as the argument.')
    else:
        bot = GoBot(argv[1])
        bot.start()
