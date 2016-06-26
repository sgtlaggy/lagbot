# discordbot

This is a [Discord](https://discordapp.com) bot built using [discord.py by Danny/Rapptz](https://github.com/rapptz/discord.py).

Create a `config.json` file in the same folder as `bot.py` with the following contents:

```
{
    "owner_name": "name#discriminator",
    "bot_token": "secret bot token"
}
```

To be able to use owner-only commands (only those in `REPL.py` as of writing this) put your user ID in `cogs/utils/checks.py` in place of mine.

If you don't want others to know you are the owner of the bot, remove the `owner_name` line.
