from collections import OrderedDict, namedtuple
import traceback
import datetime
import logging
import json

from discord.ext import commands
import discord
import aiohttp
import asyncpg

from cogs.utils.utils import pluralize, TIME_BRIEF, TIME_LONG, tb_args


Response = namedtuple('Response', 'status data')


class LagBot(commands.Bot):
    def __init__(self, *args, config_file, debug=False, **kwargs):
        self._debug = debug
        self.config_file = config_file
        with open(config_file) as fp:
            self.config = json.load(fp, object_pairs_hook=OrderedDict)
        super().__init__(*args, **kwargs)
        if self._debug:
            self.command_prefix = '?!'
        useragent = 'Discord Bot'
        source = self.config.get('source')
        if source is not None:
            useragent += ' ' + source
        self._http = aiohttp.ClientSession(
            loop=self.loop,
            headers={'User-Agent': useragent})
        self.db = self.loop.run_until_complete(
            asyncpg.connect(
                database='lagbot',
                loop=self.loop))

    async def logout(self):
        await self._http.close()
        await self.db.close()
        await super().logout()

    def _logout(self):
        self.loop.create_task(self.logout())

    def run(self, *args, **kwargs):
        super().run(self.config['bot_token'], *args, **kwargs)

    async def on_ready(self):
        if 'start_time' in dir(self):
            logging.info('Ready again.')
            return
        self.start_time = datetime.datetime.utcnow()
        if None in {self.config.get('client_id'), self.config.get('owner_id')}:
            app_info = await self.application_info()
            self.client_id = app_info.id
            self.owner = app_info.owner
            self.config['client_id'] = self.client_id
            self.config['owner_id'] = self.owner.id
            with open(self.config_file, 'w') as fp:
                json.dump(self.config, fp, indent=4)
        else:
            self.client_id = self.config.get('client_id')
            self.owner = await self.get_user_info(self.config['owner_id'])
        game = self.config.get('game')
        if game is not None:
            await self.change_presence(game=discord.Game(name=game))
        if self._debug:
            logging.info('Ready.')

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)

    async def on_command_error(self, exc, ctx):
        """Emulate default on_command_error and add guild + channel info."""
        if hasattr(ctx.command, 'on_error') or isinstance(exc, commands.CommandNotFound):
            return
        logging.warning(f'Ignoring exception in command {ctx.command}')
        if isinstance(ctx.message.channel, (discord.DMChannel, discord.GroupChannel)):
            if str(ctx.message.channel.type) == 'group':
                msg = 'Message was "{0.content}" by {0.author} in {0.channel}.'
            else:
                msg = 'Message was "{0.content}" in {0.channel}.'
        else:
            msg = 'Message was "{0.content}" by {0.author} in "{0.channel}" on "{0.guild}".'
        msg = msg.format(ctx.message)

        exc = getattr(exc, 'original', exc)
        tb = ''.join(traceback.format_exception(*tb_args(exc)))
        logging.error('\n'.join((msg, tb)))

        if not self._debug:
            try:
                await self.owner.send(f'{msg}\n```py\n{tb}\n```'.format(msg, tb))
            except:
                pass

    async def request(self, url, _type='json', *, timeout=10, method='GET', **kwargs):
        if _type not in {'json', 'read', 'text'}:
            return
        if kwargs.get('data') and method == 'GET':
            method = 'POST'
        async with self._http.request(method, url, timeout=timeout, **kwargs) as resp:
            data = None
            try:
                data = await getattr(resp, _type)()
            except:
                logging.exception(f'Failed getting type {_type} from "{url}".')
            return Response(resp.status, data)

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
