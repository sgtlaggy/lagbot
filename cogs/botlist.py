import asyncio
import logging
import json

from .base import BaseCog
import config

CARBON_API = 'https://www.carbonitex.net/discord/data/botdata.php'
DBOTSPW_API = 'https://bots.discord.pw/api/bots/{.user.id}/stats'
DBOTSORG_API = 'https://discordbots.org/api/bots/{.user.id}/stats'


class BotList(BaseCog):
    """Most code here was adapted from R. Danny's carbonitex cog."""
    def __init__(self, bot):
        super().__init__(bot)
        self.carbon_key = getattr(config, 'carbon_key', None)
        self.dbotspw_key = getattr(config, 'dbotspw_key', None)
        self.dbotsorg_key = getattr(config, 'dbotsorg_key', None)

    async def update(self, *args, **kwargs):
        guilds = len(self.bot.guilds)
        if self.carbon_key is not None:
            carbon_payload = {'key': self.carbon_key,
                              'servercount': guilds}
            try:
                resp = await self.bot.request(CARBON_API, data=carbon_payload, type_='text')
            except asyncio.TimeoutError:
                logging.info(f'Carbon failed to respond for\n{json.dumps(carbon_payload, indent=2)}')
            else:
                logging.info(f'Carbon returned {resp.status} for\n{json.dumps(carbon_payload, indent=2)}')

        for site, link, key in (('DBots.pw', DBOTSPW_API, self.dbotspw_key),
                                ('DBots.org', DBOTSORG_API, self.dbotsorg_key)):
            if key is not None:
                dbots_payload = {'server_count': guilds}
                dbots_headers = {'authorization': key,
                                 'content-type': 'application/json'}
                try:
                    resp = await self.bot.request(link.format(self.bot), data=dbots_payload,
                                                  headers=dbots_headers, type_='text')
                except asyncio.TimeoutError:
                    logging.info(f'{site} failed to respond for\n{json.dumps(dbots_payload, indent=2)}')
                else:
                    logging.info(f'{site} returned {resp.status} for\n{json.dumps(dbots_payload, indent=2)}')

    on_ready = update
    on_guild_join = update
    on_guild_remove = update


def setup(bot):
    bot.add_cog(BotList(bot))
