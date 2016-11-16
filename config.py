DEBUG = True

CHANNEL = 'random'

ALIASES = {
    'RANDOM': ['random', ':troll:', ':trollface:'],
    'PASS': ['pass', 'skip'],
    'RESIGN': ['resign', 'giveup'],
}

# How often to play moves. See `man crontab` for format information.
#CRON = '0 9-18 * * 1-5' # Hourly between 9:00 and 18:00 on weekdays.
CRON = '*/2 * * * *' # Every two minutes.
