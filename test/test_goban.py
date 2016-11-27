import unittest
from unittest.mock import MagicMock
from goban import Goban, Move

class TestVoteMove(unittest.TestCase):
    def setUp(self):
        self.goban = Goban()
        self.goban.votes = {}
        self.goban.vote_random = MagicMock()

        self.a1_move = Move('a1')
        self.a2_move = Move('a2')
        self.random_move = Move('random')

    def test_vote_succeeds(self):
        self.goban.is_valid = MagicMock(return_value=True)

        vote_move_result = self.goban.vote_move(self.a1_move, 'user')

        self.assertEqual(self.goban.votes['user'], self.a1_move)
        self.assertEqual(vote_move_result, 'Voted for `A1`.')

    def test_invalid_move(self):
        self.goban.is_valid = MagicMock(return_value=False)

        vote_move_result = self.goban.vote_move(self.a1_move, 'user')

        self.assertEqual(self.goban.votes, {})
        self.assertEqual(vote_move_result, '`A1` seems to be an invalid move.')

    def test_already_voted(self):
        self.goban.is_valid = MagicMock(return_value=True)
        self.goban.votes = {'user': self.a1_move}

        vote_move_result = self.goban.vote_move(self.a1_move, 'user')

        self.assertEqual(self.goban.votes['user'], self.a1_move)
        self.assertEqual(vote_move_result, "You've already voted for `A1`!")

    def test_change_vote(self):
        self.goban.is_valid = MagicMock(return_value=True)
        self.goban.votes = {'user': self.a2_move}

        vote_move_result = self.goban.vote_move(self.a1_move, 'user')

        self.assertEqual(self.goban.votes['user'], self.a1_move)
        self.assertEqual(vote_move_result, 'Changed vote from `A2` to `A1`!')

    def test_vote_random(self):
        self.goban.vote_move(self.random_move, 'user')

        self.goban.vote_random.assert_called_with('user', self.random_move.hidden)



if __name__ == '__main__':
    unittest.main()
