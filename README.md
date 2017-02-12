# Go Slack Bot
Play [go](http://senseis.xmp.net/?WhatIsGo) amongst a Slack team by voting on moves. By default the move with the highest vote after one hour is played.

## Installation
1. Create a new [bot user integration in Slack](https://my.slack.com/services/new/bot), naming it `@hikaru` and taking note of its API token.
2. `git clone git@github.com:shobute/go-slack.git`
3. `cd go-slack`
4. `python3 -m venv venv && source venv/bin/activate`
5. `pip install -r requirements.txt`
6. `python3 gobot.py API_TOKEN` (Replacing `API_TOKEN` with the token from step 1.)

If you would like to change the name/channel/etc. you can update the [config](config.py).

## Use
The bot listens out for any time it is mentioned. You may ask it to register a *vote* for a specific move (of the form `a12`), *pass*, *resign*, list *votes*, list *captures*, *show* the board, etc. For the full vocabulary it understands take a look at the [config](config.py).

If you ask the bot to vote on a move in a private message, your move is hidden from other users until it is played.

## Warning
This is still very much alpha software, use at your own risk.
