DEBUG = False

USERNAME = 'hikaru'

CHANNEL = 'random'

VOCAB = {
    'RANDOM': ['random', ':troll:', ':trollface:'],
    'PASS': ['pass', 'skip'],
    'RESIGN': ['resign', 'give up'],
    'VOTE': ['vote', 'move', 'play'],
    'VOTES': ['votes', 'moves', 'voted', 'chance'],
    'CAPTURES': ['captures'],
    'SHOW': ['show', 'board'],
    'YES': ['yes', 'yeah', 'ya', 'y', 'ja', 'please', 'ok', 'yep'],
    'NO': ['no', 'nope', 'n', 'nee', "don't", 'cancel'],
}

RESPONSES = {
    'RESIGN_CONFIRMATION': [
        'Are you sure you want to resign?',
        'Sure?',
    ],
    'RESIGN_CANCELLED': [
        'Ok.',
        'Resignation cancelled.',
    ],
    'UNKNOWN': [
        "I don't know.",
        'What do you mean?',
        "That doesn't make any sense.",
        "I'm just a bot.",
    ],
}

# How often to play moves. See `man crontab` for format information.
if debug:
    CRON = '*/2 * * * *' # Every two minutes.
else:
    CRON = '0 9-18 * * 1-5' # Hourly between 9:00 and 18:00 on weekdays.
