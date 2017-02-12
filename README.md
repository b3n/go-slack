# Go Slack Bot
Play [go](http://senseis.xmp.net/?WhatIsGo) amongst a Slack team by voting on moves. By default the move with the highest vote after one hour is played.

## Commands
The bot listens out for any time it is mentioned. You may ask it to register a *vote* for a specific move (of the form`a12`), *pass*, *resign*, list *votes*, list *captures*, *show* the board, etc. For the full vocabulary it understands take a look at the [config](config.py).
