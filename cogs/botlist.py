import logging
import json

from .base import BaseCog

CARBON_API = 'https://www.carbonitex.net/discord/data/botdata.php'
DBOTSPW_API = 'https://bots.discord.pw/api/bots/{.user.id}/stats'
DBOTSORG_API = 'https://discordbots.org/api/bots/{.user.id}/stats'


class BotList(BaseCog):
    """Most code here was adapted from R. Danny's carbonitex cog."""
    def __init__(self, bot):
        super().__init__(bot)
        self.carbon_key = bot.config.get('carbon_key')
        self.dbotspw_key = bot.config.get('dbotspw_key')
        self.dbotsorg_key = bot.config.get('dbotsorg_key')

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

        for site, link, key in (('DBots.pw', DBOTSPW_API, self.dbotspw_key),
                                ('DBots.org', DBOTSORG_API, self.dbotsorg_key)):
            if key is not None:
                dbots_payload = {'server_count': guilds}
                dbots_headers = {'authorization': key,
                                 'content-type': 'application/json'}
                resp = await self.bot.request(link.format(self.bot),
                                              data=dbots_payload,
                                              headers=dbots_headers,
                                              ignore_timeout=True,
                                              type_='text')
                logging.info('{site} returned {.status} for\n{}'.format(resp, json.dumps(dbots_payload, indent=2)))

    on_ready = update
    on_guild_join = update
    on_guild_remove = update


def setup(bot):
    bot.add_cog(BotList(bot))
