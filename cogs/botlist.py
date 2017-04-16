import logging
import json

from .base import BaseCog

CARBON_API = 'https://www.carbonitex.net/discord/data/botdata.php'
DBOTS_API = 'https://bots.discord.pw/api/bots/{.user.id}/stats'


class BotList(BaseCog):
    """Most code here was adapted from R. Danny's carbonitex cog."""
    def __init__(self, bot):
        super().__init__(bot)
        self.carbon_key = bot.config.get('carbon_key')
        self.dbots_key = bot.config.get('dbots_key')

    async def update(self, *args, **kwargs):
        guilds = len(self.bot.guilds)
        if self.carbon_key is not None:
            carbon_payload = {'key': self.carbon_key,
                              'servercount': guilds}
            resp = await self.bot.request(CARBON_API,
                                          data=carbon_payload,
                                          ignore_timeout=True,
                                          type_='text')
            logging.info('Carbon returned {.status} for\n{}'.format(resp, json.dumps(carbon_payload, indent=2)))

        if self.dbots_key is not None:
            dbots_payload = {'server_count': guilds}
            dbots_headers = {'authorization': self.dbots_key,
                             'content-type': 'application/json'}
            resp = await self.bot.request(DBOTS_API.format(self.bot),
                                          data=dbots_payload,
                                          headers=dbots_headers,
                                          ignore_timeout=True,
                                          type_='text')
            logging.info('DBots returned {.status} for\n{}'.format(resp, json.dumps(dbots_payload, indent=2)))

    on_ready = update
    on_guild_join = update
    on_guild_remove = update


def setup(bot):
    bot.add_cog(BotList(bot))
