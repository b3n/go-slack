from collections import Counter
from typing import List, Optional, Tuple
import re
from random import choice, randrange
from imgurpython import ImgurClient
from PIL import Image


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
        self.passed = False

    def vote_move(self, move_reference: str, user: str) -> str:
        move_reference = move_reference.upper()

        if move_reference == 'RANDOM':
            return self.vote_random(user)

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

    def vote_random(self, user: str) -> str:
        # Roll the dice 9 times to find a valid move
        for _ in range(9):
            random_move_reference = chr(randrange(ord('A'), ord('S') + 1)) + str(randrange(1, 19 + 1))
            if self.is_valid(random_move_reference):
                return self.vote_move(random_move_reference, user)

        # If the board is so full that that didn't work, find all valid moves and just pick one of them
        ascii_moves = [chr(x)+str(y+1) for x in range(ord('A'), ord('S')+1) for y in range(19)]
        valid_moves = [move for move in ascii_moves if self.is_valid(move)]

        if len(valid_moves) == 0:
            return self.vote_move('PASS', user)
        return self.vote_move(choice(valid_moves), user)

    def is_valid(self, move_reference: str) -> bool:
        if move_reference in ('PASS', 'RESIGN'):
            return True

        if not self.move_pattern.match(move_reference):
            return False

        move = self.get_coordinates(move_reference)

        if move not in self.moves or self.moves[move] is not None:
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

        if move_reference == 'PASS':
            return self.pass_move()
        else:
            self.passed = False

        if move_reference == 'RESIGN':
            return self.resign()

        move = self.get_coordinates(move_reference)

        # Place stone
        self.moves[move] = self.next_turn_color
        self.next_turn_color = self._toggle_color()

        # Remove captures
        self.ko = None
        for adjacent_move in self.get_adjacent_moves(move):
            if self.moves[adjacent_move] == self.next_turn_color:
                self.remove_if_captured(adjacent_move)

        self.draw_board(move)
        return 'Playing move `{}`.\n{}'.format(move_reference, self.image_url)

    def pass_move(self) -> str:
        message = '{} passes.'.format(self.next_turn_color)

        if self.passed:
            self.restart_game()
            message += ' Game over! :tada:'
        else:
            self.next_turn_color = self._toggle_color()
            self.passed = True

        return message

    def resign(self) -> str:
        message = '{} resigns. {} wins! :tada:'.format(self.next_turn_color, self._toggle_color())

        self.restart_game()

        return message

    def restart_game(self) -> None:
        self.__init__()

    def _toggle_color(self) -> str:
        return 'white' if self.next_turn_color == 'black' else 'black'

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
        colour = self.moves[move]
        
        if not group:
            group = []
            if not self.moves[move]:
                colour = self.next_turn_color

        if colour and move not in group:
            group.append(move)
            for adjacent_move in self.get_adjacent_moves(move):
                if self.moves[adjacent_move] == colour:
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

    def draw_board(self, highlighted_move: Move) -> None:
        goban = Image.open('goban_blank.png')
        stone = {
            'black': Image.open('black.png'),
            'white': Image.open('white.png'),
        }
        shadow = Image.open('shadow.png')

        x, y = highlighted_move
        goban.paste(shadow, (x * 20 + 5, y * 20 + 5), mask=shadow)

        for x in range(19):
            for y in range(19):
                if self.moves[(x, y)]:
                    goban.paste(stone[self.moves[x, y]], (x * 20 + 10, y * 20 + 10), mask=stone[self.moves[x, y]])

        file_path = 'goban_with_moves.png'
        goban.save(file_path, 'PNG')
        upload = self.imgur_client.upload_from_path(file_path)

        self.image_url = upload['link']
