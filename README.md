UDP Tracker for Anidex
==========

Python tracking using a redis backend.
Use a unix socket at /tmp/redis.sock

Recommended usage with Pypy project for speed.

## TODO:
1. Generate transaction id using a blowfish hash instead of random bytes and verifying it.
2. Decide how to handle 'completed' in a scrap request.
3. Fork and use multiple processes since the server is currently synchronous.
