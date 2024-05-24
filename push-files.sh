#! /bin/sh

SRCS="."
DEST=pavel@clock.bogus.domain:Projects/WeatherClock

OPTS='-av --exclude-from=.rsyncignore'

rsync $OPTS $SRCS $DEST
