# discordbot

This is a [Discord](https://discordapp.com) bot built using [discord.py by Danny/Rapptz](https://github.com/rapptz/discord.py).

Create a `config.json` file in the same folder as `bot.py` with the following contents:

```
{
    "cat_api": "thecatapi api key",
    "userdocs": "https://github.com/mikevb1/discordbot/tree/master/userdocs",
    "source": "https://github.com/mikevb1/discordbot",
    "bot_token": "secret bot token"
}
```

* If you don't have or want a [TheCatAPI](http://thecatapi.com/) api key, remove the "cat\_api" line. This will prevent you from using the `!cat` command.
* If your bot isn't open-source or you don't want anyone to easily find it, remove the "source" line.
* If your bot doesn't have publicly available documentation, remove the "userdocs" line.

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
