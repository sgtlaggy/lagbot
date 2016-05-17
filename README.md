# discordbot

This is a [Discord](https://discordapp.com) bot built using [discord.py by Danny/Rapptz](https://github.com/rapptz/discord.py).

Create a `config.json` file in the same folder as `bot.py` with the following contents:

```
{
    "owner_name": "name#discriminator",
    "client_id": "oauth2 application id",
    "bot_token": "secret bot token"
}
```

If you don't want others to know you are the owner of the bot, remove the `owner_name` line.
If you don't want to allow others to invite your bot to their servers using the `!join` command, remove the `client_id` line.
