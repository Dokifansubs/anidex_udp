UDP Tracker for Anidex
==========

Python tracking using a redis backend.
Use a unix socket at /tmp/redis.sock

Recommended usage with Pypy project for speed.

## TODO:
Generate transaction id using a blowfish hash instead of random bytes and verifying it.
Decide how to handle 'completed' in a scrap request.
Fork and use multiple processes since the server id currently synchronous.
