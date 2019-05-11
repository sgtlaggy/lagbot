from collections import namedtuple
import traceback
import datetime
import asyncio
import logging
import signal
import sys

from discord.ext import commands
import discord
import aiohttp
import asyncpg

from utils.utils import UPPER_PATH, tb_args, pluralize, rzip
from utils.cache import cache
import config


Response = namedtuple('Response', 'status data')


async def command_prefix(bot, message):
    """Custom prefix function for guild-specific prefixes."""
    default = config.prefix
    if message.guild is None:
        return default
    settings = await bot.get_guild_prefix(message.guild.id)
    if settings is None:
        return commands.when_mentioned_or(default)(bot, message)
    if settings['prefix'] is None:
        return commands.when_mentioned(bot, message)
    valid = [settings['prefix']]
    if settings['allow_default']:
        if isinstance(default, (tuple, list)):
            valid.extend(default)
        else:
            valid.append(default)
    valid.sort(reverse=True)
    return commands.when_mentioned_or(*valid)(bot, message)


class LagBot(commands.Bot):
    def __init__(self, *args, debug=False, **kwargs):
        self._debug = debug
        self.game = config.game
        game = discord.Game(name=self.game)
        status = discord.Status.dnd if self._debug else discord.Status.online
        super().__init__(*args, command_prefix=command_prefix,
                         activity=game, status=status, **kwargs)
        self._before_invoke = self._before_invoke_
        self._after_invoke = self._after_invoke_
        self.resumes = 0
        self.exit_status = 0
        useragent = 'Discord Bot'
        source = config.source
        if source is not None:
            useragent += ' ' + source
        self.http_ = aiohttp.ClientSession(loop=self.loop, headers={'User-Agent': useragent})
        self.db_pool = self.loop.run_until_complete(
            asyncpg.create_pool(dsn=config.pg_dsn, command_timeout=10, loop=self.loop))

    @cache()
    async def get_guild_prefix(self, guild_id):
        async with self.db_pool.acquire() as con:
            return await con.fetchrow('''
                SELECT * FROM prefixes WHERE guild_id = $1
                ''', guild_id)

    invalidate_guild_prefix = get_guild_prefix.invalidate

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
            logging.info('Ready again.')
            self.resumes += 1
            return await self.set_game(self.game)
        self.start_time = datetime.datetime.utcnow()
        self.app = await self.application_info()
        self.owner_id = self.app.owner.id
        await self.app.owner.create_dm()
        if self._debug:
            logging.info('Ready.')

    async def on_resumed(self):
        self.resumes += 1
        await self.set_game(self.game)

    async def on_message(self, msg):
        if self._debug:
            debug_channel = config.debug_channel
            if debug_channel is None or msg.channel.id != int(debug_channel):
                return
        await self.process_commands(msg)

    async def _before_invoke_(self, ctx):
        ctx.con = await self.db_pool.acquire()

    async def _after_invoke_(self, ctx):
        await self.db_pool.release(ctx.con)

    async def on_command_error(self, ctx, exc):
        """Emulate default on_command_error and add guild + channel info."""
        if hasattr(ctx.command, 'on_error') or getattr(exc, 'handled', False) or \
                not isinstance(exc, commands.CommandInvokeError) or isinstance(exc.original, discord.Forbidden):
            return
        msg = f'{ctx.message.content}\nin {"guild" if ctx.guild else "DM"}'
        tb = ''.join(traceback.format_exception(*tb_args(exc.original))).replace(UPPER_PATH, '...')
        logging.error('\n'.join((msg, tb)))

    async def wait_for(self, *args, ignore_timeout=False, **kwargs):
        """Override default wait_for to allow ignoring TimeoutError."""
        if ignore_timeout:
            try:
                return await super().wait_for(*args, **kwargs)
            except asyncio.TimeoutError:
                return None
        else:
            return await super().wait_for(*args, **kwargs)

    async def _request(self, url, type_='json', *, timeout=10, method='GET', **kwargs):
        if type_ not in {'json', 'read', 'text'}:
            return
        if kwargs.get('data') and method == 'GET':
            method = 'POST'
        async with self.http_.request(method, url, timeout=timeout, **kwargs) as resp:
            data = None
            try:
                data = await getattr(resp, type_)()
            except:
                logging.exception(f'Failed getting type {type_} from "{url}".')
            return Response(resp.status, data)

    async def request(self, *args, ignore_timeout=True, **kwargs):
        """Utility request function.

        type_ is the method to get data from response
        """
        if ignore_timeout:
            try:
                return await self._request(*args, **kwargs)
            except asyncio.TimeoutError:
                return Response(None, None)
        else:
            return await self._request(*args, **kwargs)

    async def set_game(self, name):
        if name is not None:
            game = discord.Game(name=f'{name} {self.resumes or ""}')
        await self.change_presence(activity=game, status=discord.Status.dnd if self._debug else discord.Status.online)
        self.game = name

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
