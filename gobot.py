from time import sleep, time
from datetime import datetime
import re
from random import choice
from sys import argv
from collections import Counter
from typing import List, Optional, Tuple
from pickle import dump, load

from slackclient import SlackClient
from imgurpython import ImgurClient
from PIL import Image, ImageDraw


DEBUG = True


class Goban:
    Move = Tuple[int, int]
    Group = List[Move]

    def __init__(self) -> None:
        self.votes = {}
        self.image_url = 'https://i.imgur.com/iWzRKV0.png'
        self.imgur_client = ImgurClient('6584aa67fc46a02', 'fda614da4406c63a395bd0748c1fb74adeccc5ef')
        self.move_pattern = re.compile(r'^([a-t])([1-9]|1[0-9])$', re.IGNORECASE)
        self.next_turn_color = 'black'
        self.moves = {(x, y): None for x in range(19) for y in range(19)}
        self.ko = None

    def vote_move(self, move_reference: str, user: str) -> str:
        move_reference = move_reference.upper()

        if move_reference == 'PASS':
            return '// TODO: Implement passing and end game... :robot_face:'

        if not self.move_pattern.match(move_reference):
            return "Oops, I don't understand `{}`, is that supposed to be somewhere on the board?".format(move_reference)

        if not self.is_valid(move_reference):
            return '`{}` seems to be an invalid move.'.format(move_reference)

        if user in self.votes:
            if self.votes[user] == move_reference:
                return "You've already voted for `{}`!".format(move_reference)
            else:
                old_move = self.votes[user]
                self.votes[user] = move_reference
                return 'Changed vote from `{}` to `{}`!'.format(old_move, move_reference)

        self.votes[user] = move_reference
        return 'Voted for `{}`.'.format(move_reference)

    def is_valid(self, move_reference: str) -> bool:
        move = self.get_coordinates(move_reference)

        if self.moves[move] is not None:
            return False

        if self.get_liberties(self.build_group(move)) > 0:
            return True

        if self.ko == move:  # TODO: Superko
            return False

        for adjacent_move in self.get_adjacent_moves(move):
            # If an adjacent move is in atari then playing this move will capture it, giving us a liberty.
            if self.get_liberties(self.build_group(adjacent_move)) == 1:
                return True

        return False

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

        move_reference = choice(list(self.votes.values()))
        self.votes = {}

        move = self.get_coordinates(move_reference)

        # Place stone
        self.moves[move] = self.next_turn_color
        self.next_turn_color = 'white' if self.next_turn_color == 'black' else 'black'

        # Remove captures
        self.ko = None
        for adjacent_move in self.get_adjacent_moves(move):
            if self.moves[adjacent_move] == self.next_turn_color:
                self.remove_if_captured(adjacent_move)

        self.draw_board()
        return 'Playing move `{}`.\n{}'.format(move_reference, self.image_url)

    def get_coordinates(self, move_reference: str) -> (int, int):
        move_coords = self.move_pattern.match(move_reference).groups()

        x = ord(move_coords[0].upper()) - ord('A')
        y = 19 - int(move_coords[1])

        return x, y

    def remove_if_captured(self, move: Move) -> None:
        group = self.build_group(move)
        if self.get_liberties(group) == 0:
            if len(group) == 1:
                self.ko = group[0]

            for group_move in group:
                self.moves[group_move] = None

    def get_liberties(self, group: Group) -> bool:
        liberties = 0

        for group_move in group:
            for adjacent_move in self.get_adjacent_moves(group_move):
                if self.moves[adjacent_move] is None:
                    liberties += 1

        return liberties

    def build_group(self, move: Move, group: Optional[Group]=None) -> Group:
        if not group:
            group = []

        if (len(group) == 0 or self.moves[move]) and move not in group:
            group.append(move)
            for adjacent_move in self.get_adjacent_moves(move):
                if self.moves[adjacent_move] == self.moves[move]:
                    group = self.build_group(adjacent_move, group)

        return group

    def get_adjacent_moves(self, move: Move) -> Group:
        x, y = move
        adjacent_moves = []

        if x + 1 < 19:
            adjacent_moves.append((x + 1, y))

        if y + 1 < 19:
            adjacent_moves.append((x, y + 1))

        if x - 1 >= 0:
            adjacent_moves.append((x - 1, y))

        if y - 1 >= 0:
            adjacent_moves.append((x, y - 1))

        return adjacent_moves

    def show_board(self) -> str:
        return self.image_url

    def draw_board(self) -> None:
        im = Image.open('goban_blank.png')

        draw = ImageDraw.Draw(im)
        for x in range(19):
            for y in range(19):
                if self.moves[(x, y)]:
                    draw.ellipse([(x * 20 + 10, y * 20 + 10), (x * 20 + 30, y * 20 + 30)], fill=self.moves[(x, y)])

        file_path = 'goban_with_moves.png'
        im.save(file_path, 'PNG')
        upload = self.imgur_client.upload_from_path(file_path)

        self.image_url = upload['link']


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

                    if DEBUG:
                        print(event)

                self.hourly_crons()
                self.ping()
                sleep(1)
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
