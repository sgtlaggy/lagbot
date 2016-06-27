# discordbot

This is a [Discord](https://discordapp.com) bot built using [discord.py by Danny/Rapptz](https://github.com/rapptz/discord.py).

Create a `config.json` file in the same folder as `bot.py` with the following contents:

```
{
    "owner_name": "name#discriminator",
    "owner_id": "owner's user ID",
    "bot_token": "secret bot token"
}
```

* If you want others to know you are the owner of the bot put your name and discriminator in place of `name#discriminator`, otherwise remove the `owner_name` line.
* If you want to use owner-only commands (those in `cogs/REPL.py` as of writing this) put our user ID in place of `owner's user ID`, otherwise remove the `owner_id` line.
