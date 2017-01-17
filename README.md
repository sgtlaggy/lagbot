# discordbot

This is a [Discord](https://discordapp.com) bot built using [discord.py by Danny/Rapptz](https://github.com/rapptz/discord.py).

If you don't have or want to include config attributes, remove them from the config file. They all have fallbacks except `bot_token`.
---

#### This bot requires you run Postgresql for the Overwatch, Images (XKCD), and Tags cogs.

Before running the bot, you must create a new database owned by the "postgres" user and add 4 tables to it.

These are the commands to run in the psql prompt to do this:

1. `CREATE DATABASE lagbot;`
2. `\c lagbot`
3. `CREATE TABLE overwatch (id text PRIMARY KEY, btag text, mode text);`
4. `CREATE TABLE xkcd (num integer PRIMARY KEY, safe_title text, alt text, img text, date date);`
5. `CREATE TABLE tags (name text PRIMARY KEY, content text, uses integer DEFAULT 0, owner_id text, modified_at timestamp without time zone DEFAULT (now() at time zone 'utc'));`
6. `CREATE TABLE tagusers (id text PRIMARY KEY, uses integer DEFAULT 1);`

##### For Overwatch stats, you have 2 options:

1. Run your own instance of [OW API](https://github.com/sundwarf/owapi)
2. Change `127.0.0.1:4444` in `Overwatch.py` to `owapi.net`
