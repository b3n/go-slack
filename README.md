# Go Slack Bot
Play [go](http://senseis.xmp.net/?WhatIsGo) amongst a Slack team by voting on moves. By default the move with the highest vote after one hour is played.

## Commands
* __`!vote`__: Vote on the next move, takes arguments of the form `a12` for a specific position, or `random`, `pass`, `resign`. For example `!vote pass` places a vote to pass on the next turn.
* __`!votes`__: Show the current votes for the next move.
* __`!captures`__: Show how many captures each side has.
* __`!show`__: Show (as an image) the current state of the board.
