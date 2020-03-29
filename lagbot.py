from collections import namedtuple
import traceback
import datetime
import asyncio
import logging

from discord.ext import commands
import discord
import aiohttp
import asyncpg

from utils import UPPER_PATH, tb_args, pluralize, rzip
import config

Response = namedtuple('Response', 'status data')


class LagBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         command_prefix=commands.when_mentioned_or(config.prefix),
                         help_command=commands.DefaultHelpCommand(command_attrs={'hidden': True}),
                         activity=discord.Activity(type=discord.ActivityType[config.activity], name=config.activity_name),
                         **kwargs)
        self.exit_status = 0
        useragent = 'Discord Bot'
        source = config.source
        if source is not None:
            useragent += ' ' + source
        self.http_ = aiohttp.ClientSession(loop=self.loop, headers={'User-Agent': useragent})
        self.db_pool = self.loop.run_until_complete(
            asyncpg.create_pool(dsn=config.pg_dsn, command_timeout=10, loop=self.loop))

    async def close(self):
        if self._closed:
            return
        await self.http_.close()
        await self.db_pool.close()
        await super().close()

    def run(self, *args, **kwargs):
        super().run(config.token, *args, **kwargs)
        return self.exit_status

    async def on_ready(self):
        if hasattr(self, 'start_time'):
            return
        self.start_time = datetime.datetime.utcnow()
        self.app = app = await self.application_info()
        if app.team:
            self.owner_ids = {m.id for m in app.team.members}
        else:
            self.owner_id = app.owner.id

    async def on_command_error(self, ctx, exc):
        """Emulate default on_command_error and add guild + channel info."""
        if hasattr(ctx.command, 'on_error') or getattr(exc, 'handled', False) or \
                not isinstance(exc, commands.CommandInvokeError) or isinstance(exc.original, discord.Forbidden):
            return
        tb = ''.join(traceback.format_exception(*tb_args(exc.original))).replace(UPPER_PATH, '...')
        logging.error(tb)

    async def request(self, url, type_='json', *, timeout=10, method='GET', **kwargs):
        if type_ not in {'json', 'read', 'text'}:
            return
        if kwargs.get('data') and method == 'GET':
            method = 'POST'
        try:
            async with self.http_.request(method, url, timeout=timeout, **kwargs) as resp:
                data = None
                try:
                    data = await getattr(resp, type_)()
                except:  # NOQA
                    logging.exception(f'Failed getting type {type_} from "{url}".')
                return Response(resp.status, data)
        except asyncio.TimeoutError:
            return Response(None, None)

    def get_uptime(self, brief=False):
        now = datetime.datetime.utcnow()
        delta = now - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if brief:
            fmt = ('{n}{s}',) * 4
            units = ('dd', 'hh', 'mm', 'ss')
            joiner = ' '
        else:
            fmt = ('{n} {s}',) * 4
            units = (('day', 'days'), ('hour', 'hours'), ('minute', 'minutes'), ('second', 'seconds'))
            joiner = ', '

        for ind, time in enumerate((days, hours, minutes, seconds, None)):
            if time:
                fmt = fmt[ind:]
                break
            elif time is None:
                fmt = [fmt[3]]

        return joiner.join(pluralize(*u, t, f) for u, t, f in rzip(units, (days, hours, minutes, seconds), fmt))
