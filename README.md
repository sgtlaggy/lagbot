# discordbot

This is a [Discord](https://discordapp.com) bot built using [discord.py by Danny/Rapptz](https://github.com/rapptz/discord.py).

If you don't have or want to include config attributes, remove them from the config file. They all have fallbacks except `bot_token`.
---

#### This bot requires you run Postgresql for the Overwatch, Images (XKCD), and Tags cogs.

Before running the bot, you must create a new database owned by the `postgres` user and add several tables to it.
To do this, run this command as the `postgres` user in this directory:

    psql -f create_db.sql

##### For Overwatch stats, you have 2 options:

1. Run your own instance of [OW API](https://github.com/sundwarf/owapi)
2. Change `127.0.0.1:4444` in `Overwatch.py` to `owapi.net`
