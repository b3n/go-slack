from collections import Counter
from copy import deepcopy
from random import choice, randrange
from typing import List, Optional, Tuple
import re

from imgurpython import ImgurClient
from PIL import Image

import config


class Move:
    MOVE_PATTERN = re.compile(r'\b([a-t])([1-9]|1[0-9])\b', re.IGNORECASE)

    def __init__(self, move_reference: str, hidden: bool=False) -> None:
        self.move_reference = move_reference.upper()
        self.hidden = hidden

    def __eq__(self, other) -> bool:
        return self.move_reference == other.move_reference

    def __str__(self) -> str:
        return '`SURPRISE`' if self.hidden else '`{}`'.format(self.move_reference)

    def __hash__(self) -> int:
        return hash(self.move_reference)


    @classmethod
    def from_coordinates(cls, x: int, y: int, hidden: bool=False):
        return cls(chr(ord('A') + x) + str(19 - y), hidden)

    @property
    def coordinates(self) -> Optional[Tuple[int, int]]:
        move_match = self.MOVE_PATTERN.match(self.move_reference)

        if move_match:
            move_coords = move_match.groups()

            x = ord(move_coords[0]) - ord('A')
            y = 19 - int(move_coords[1])

            return x, y


class Goban:
    Group = List[Move]

    def __init__(self) -> None:
        self.votes = {}
        self.image_url = 'https://i.imgur.com/iWzRKV0.png'
        self.imgur_client = ImgurClient('6584aa67fc46a02', 'fda614da4406c63a395bd0748c1fb74adeccc5ef')
        self.next_turn_color = 'black'
        self.moves = {(x, y): None for x in range(19) for y in range(19)}
        self.history = [{**self.moves, 'player': self.next_turn_color}]
        self.captures = {'black': 0, 'white': 0}
        self.passed = False

        config.VOCAB.update({k: [alias.upper() for alias in v] for k, v in config.VOCAB.items()})

    def vote_move(self, move: Move, user: str) -> str:
        if not self.is_valid(move):
            return '{} seems to be an invalid move.'.format(move)

        if user in self.votes:
            if self.votes[user] == move:
                return "You've already voted for {}!".format(move)
            else:
                old_move = self.votes[user]
                self.votes[user] = move
                return 'Changed vote from {} to {}!'.format(old_move, move)

        self.votes[user] = move
        return 'Voted for {}.'.format(move)

    def vote_random(self, user: str, hidden: bool) -> str:
        # Roll the dice 9 times to find a valid move
        for _ in range(9):
            random_move = Move.from_coordinates(randrange(0, 19), randrange(0, 19), hidden)
            if self.is_valid(random_move):
                return self.vote_move(random_move, user)

        # If the board is so full that that didn't work, find all valid moves and just pick one of them
        all_moves = [Move.from_coordinates(x, y, hidden) for x in range(19) for y in range(19)]
        valid_moves = [move for move in all_moves if self.is_valid(move)]

        if len(valid_moves) == 0:
            return self.vote_move(Move('pass', hidden), user)
        else:
            return self.vote_move(choice(valid_moves), user)

    def is_valid(self, move: Move) -> bool:
        if not move.coordinates:
            return False

        if move.coordinates not in self.moves or self.moves[move.coordinates] is not None:
            return False

        if self.get_liberties(self.build_group(move)) > 0:
            return not self.superko(move)

        for adjacent_move in self.get_adjacent_moves(move):
            # If an adjacent move is in atari then playing this move will capture it, giving us a
            # liberty.
            if self.get_liberties(self.build_group(adjacent_move)) == 1:
                return not self.superko(move)

        return False

    def superko(self, move: Move) -> bool:
        # check if this move would return us to an earlier game state.
        potential_game_state = deepcopy(self)
        potential_game_state.place_stone(move)
        return potential_game_state.current_game_state() in self.history

    def get_votes(self) -> str:
        if len(self.votes) == 0:
            return 'No votes.'

        vote_counts = Counter(self.votes.values())
        vote_percentages = [(move, vote_counts[move] / len(self.votes)) for move in vote_counts]

        message = ''
        for move, percentage in vote_percentages:
            message += '{} {:.0%} chance of being played.\n'.format(move, percentage)

        return message

    def play_move(self) -> Optional[str]:
        if len(self.votes) == 0:
            return None

        move = choice(list(self.votes.values()))
        move.hidden = False
        self.votes = {}

        self.passed = False

        self.place_stone(move)

        self.history.append(self.current_game_state())
        self.draw_board(move)
        return 'Playing move {}.\n{}'.format(move, self.image_url)

    def place_stone(self, move: Move) -> None:
        # Place stone
        self.moves[move.coordinates] = self.next_turn_color
        self.next_turn_color = self._toggle_color()

        # Remove captures
        for adjacent_move in self.get_adjacent_moves(move):
            if self.moves[adjacent_move.coordinates] == self.next_turn_color:
                self.remove_if_captured(adjacent_move)

    def pass_move(self) -> str:
        message = '{} passes.'.format(self.next_turn_color)

        if self.passed:
            self.restart_game()
            message += ' Game over! :tada:'
        else:
            self.next_turn_color = self._toggle_color()
            self.passed = True
            self.history.append(self.current_game_state())

        return message

    def resign(self) -> str:
        self.restart_game()
        return '{} resigns. {} wins! :tada:'.format(self.next_turn_color, self._toggle_color())

    def restart_game(self) -> None:
        self.__init__()

    def _toggle_color(self) -> str:
        return 'white' if self.next_turn_color == 'black' else 'black'

    def current_game_state(self) -> dict:
        return {**self.moves, 'player': self.next_turn_color}

    def remove_if_captured(self, move: Move) -> None:
        group = self.build_group(move)
        if self.get_liberties(group) == 0:
            self.captures[self._toggle_color()] += len(group)
            for group_move in group:
                self.moves[group_move.coordinates] = None

    def get_liberties(self, group: Group) -> bool:
        liberties = 0

        for group_move in group:
            for adjacent_move in self.get_adjacent_moves(group_move):
                if self.moves[adjacent_move.coordinates] is None:
                    liberties += 1

        return liberties

    def build_group(self, move: Move, group: Optional[Group]=None) -> Group:
        colour = self.moves[move.coordinates]

        if not group:
            group = []
            if not self.moves[move.coordinates]:
                colour = self.next_turn_color

        if colour and move not in group:
            group.append(move)
            for adjacent_move in self.get_adjacent_moves(move):
                if self.moves[adjacent_move.coordinates] == colour:
                    group = self.build_group(adjacent_move, group)

        return group

    def get_adjacent_moves(self, move: Move) -> Group:
        x, y = move.coordinates
        adjacent_moves = []

        if x + 1 < 19:
            adjacent_moves.append(Move.from_coordinates(x + 1, y))

        if y + 1 < 19:
            adjacent_moves.append(Move.from_coordinates(x, y + 1))

        if x - 1 >= 0:
            adjacent_moves.append(Move.from_coordinates(x - 1, y))

        if y - 1 >= 0:
            adjacent_moves.append(Move.from_coordinates(x, y - 1))

        return adjacent_moves

    def show_board(self) -> str:
        return self.image_url

    def get_captures(self) -> str:
        return 'Number of stones captured by each player:\nBlack: {}\nWhite: {}'.format(
            self.captures['black'], self.captures['white'])

    def draw_board(self, highlighted_move: Move) -> None:
        goban = Image.open('goban_blank.png')
        stone = {
            'black': Image.open('black.png'),
            'white': Image.open('white.png'),
        }
        shadow = Image.open('shadow.png')

        x, y = highlighted_move.coordinates
        goban.paste(shadow, (x * 20 + 5, y * 20 + 5), mask=shadow)

        for x in range(19):
            for y in range(19):
                if self.moves[(x, y)]:
                    goban.paste(stone[self.moves[x, y]],
                                (x * 20 + 10, y * 20 + 10),
                                mask=stone[self.moves[x, y]])

        file_path = 'goban_with_moves.png'
        goban.save(file_path, 'PNG')
        upload = self.imgur_client.upload_from_path(file_path)

        self.image_url = upload['link']
