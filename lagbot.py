from collections import OrderedDict, namedtuple
import traceback
import datetime
import asyncio
import logging
import json
import uuid
import os

from discord.ext import commands
import discord
import aiohttp
import asyncpg

from utils.utils import pluralize, TIME_BRIEF, TIME_LONG, tb_args, db_decode


Response = namedtuple('Response', 'status data')


IGNORE_EXCS = (discord.Forbidden,  # people keep disallowing send_messages
               commands.CommandNotFound,
               commands.MissingRequiredArgument,
               commands.NoPrivateMessage)


async def command_prefix(bot, message):
    """Custom prefix function for guild-specific prefixes."""
    default = bot.default_prefix
    if message.guild is None:
        return default
    async with bot.db_pool.acquire() as con:
        settings = await con.fetchrow('''
            SELECT * FROM prefixes WHERE guild_id = $1
            ''', str(message.guild.id))
    if settings is None:
        return default
    prefix, allow_default = settings['prefix'], settings['allow_default']
    valid = [db_decode(prefix)]
    if allow_default:
        if isinstance(default, (tuple, list)):
            valid.extend(default)
        else:
            valid.append(default)
    return valid


class LagBot(commands.Bot):
    def __init__(self, *args, config_file, debug=False, **kwargs):
        self._debug = debug
        self.loop = kwargs.get('loop', asyncio.get_event_loop())
        self.config_file = config_file
        self.config_lock = asyncio.Lock(loop=self.loop)
        self.loop.run_until_complete(self.load_config())
        self.game = self.config.get('game')
        status = discord.Status.dnd if self._debug else discord.Status.online
        game = self.game if self.game is None else discord.Game(name=self.game)
        super().__init__(*args, game=game, status=status, loop=self.loop, **kwargs)
        self._before_invoke = self._before_invoke_
        self._after_invoke = self._after_invoke_
        self.default_prefix = self.command_prefix
        self.resumes = 0
        if self._debug:
            self.command_prefix = '?!'
        else:
            self.command_prefix = command_prefix
        useragent = 'Discord Bot'
        source = self.config.get('source')
        if source is not None:
            useragent += ' ' + source
        self.http_ = aiohttp.ClientSession(loop=self.loop, headers={'User-Agent': useragent})
        self.db_pool = self.loop.run_until_complete(
            asyncpg.create_pool(database='lagbot', command_timeout=10, loop=self.loop))

    def _config_to_file(self):
        app_path, config_file = os.path.split(self.config_file)
        temp = os.path.join(app_path, f'{uuid.uuid4()}-{config_file}.tmp')
        with open(temp, 'w', encoding='utf-8') as fp:
            json.dump(self.config.copy(), fp, indent=4, ensure_ascii=True)
        os.replace(temp, self.config_file)

    def _config_from_file(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as fp:
                self.config = json.load(fp, object_pairs_hook=OrderedDict)
        except FileNotFoundError:
            self.config = {}

    async def save_config(self):
        with await self.config_lock:
            await self.loop.run_in_executor(None, self._config_to_file)

    async def load_config(self):
        with await self.config_lock:
            await self.loop.run_in_executor(None, self._config_from_file)

    async def logout(self):
        await self.http_.close()
        await self.db_pool.close()
        await super().logout()

    def logout_(self):
        """Mainly for use in signal handler, may have other uses."""
        self.loop.create_task(self.logout())

    def run(self, *args, **kwargs):
        super().run(self.config['bot_token'], *args, **kwargs)
        try:
            return self.exit_status
        except AttributeError:
            return 0

    async def on_ready(self):
        if hasattr(self, 'start_time'):
            logging.info('Ready again.')
            self.resumes += 1
            await self.set_game(self.game)
            return
        self.start_time = datetime.datetime.utcnow()
        self.app = await self.application_info()
        self.owner_id = self.app.owner.id
        if self._debug:
            logging.info('Ready.')

    async def on_resumed(self):
        self.resumes += 1
        await self.set_game(self.game)

    async def on_message(self, msg):
        if msg.author.bot:
            return
        if self._debug:
            debug_channel = self.config.get('debug_channel')
            if debug_channel is None or msg.channel.id != int(debug_channel):
                return
        await self.process_commands(msg)

    async def _before_invoke_(self, ctx):
        if getattr(ctx.command, '_db', False):
            ctx.con = await self.db_pool.acquire()

    async def _after_invoke_(self, ctx):
        try:
            await self.db_pool.release(ctx.con)
        except AttributeError:
            pass

    async def on_command_error(self, ctx, exc):
        """Emulate default on_command_error and add guild + channel info."""
        original = getattr(exc, 'original', exc)
        if hasattr(ctx.command, 'on_error') or getattr(exc, 'handled', False) or isinstance(original, IGNORE_EXCS):
            return
        logging.warning(f'Ignoring exception in command {ctx.command}')
        msg = f'{ctx.message.content}\nin {"guild" if ctx.guild else "DM"}'
        outer_path = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
        tb = ''.join(traceback.format_exception(*tb_args(original))).replace(outer_path, '...')
        logging.error('\n'.join((msg, tb)))

        if not self._debug and isinstance(exc, commands.CommandInvokeError):
            try:
                await self.app.owner.send(f'{msg}\n```py\n{tb}\n```'.format(msg, tb))
            except:
                pass

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

    async def set_game(self, game=None):
        self.game = game
        status = None
        for guild in self.guilds:
            if isinstance(guild.me, discord.Member):
                status = guild.me.status
                break
        if game is None:
            game = 'Resumes:'
            if self.resumes == 0:
                await self.change_presence(status=status)
                return
        await self.change_presence(game=discord.Game(name=f'{game} {self.resumes or ""}'), status=status)

    def get_uptime(self, brief=False):
        now = datetime.datetime.utcnow()
        delta = now - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if brief:
            fmt = TIME_BRIEF
            joiner = ' '
        else:
            fmt = TIME_LONG
            joiner = ', '

        for ind, time in enumerate((days, hours, minutes, seconds, None)):
            if time:
                fmt = fmt[ind:]
                break
            elif time is None:
                fmt = [fmt[3]]

        return pluralize(joiner.join(fmt).format(d=days, h=hours, m=minutes, s=seconds))
