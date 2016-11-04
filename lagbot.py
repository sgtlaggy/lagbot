from collections import OrderedDict
import traceback
import datetime
import json
import sys

from discord.ext import commands
import discord
import aiohttp
import asyncpg


class LagBot(commands.Bot):
    def __init__(self, *args, config_file, debug=False, **kwargs):
        self._debug = debug
        self.config_file = config_file
        with open(config_file) as fp:
            self.config = json.load(fp)
        self.owner = discord.User(**self.config.pop('owner')) if 'owner' in self.config else None
        self.client_id = self.config.pop('client_id') if 'client_id' in self.config else None
        super().__init__(*args, **kwargs)
        if self._debug:
            self.command_prefix = '%!'
        useragent = 'Discord Bot'
        source = self.config.get('source')
        if source is not None:
            useragent += ' ' + source
        self.aiohsession = aiohttp.ClientSession(
            loop=self.loop,
            headers={'User-Agent': useragent})
        self.db = self.loop.run_until_complete(
            asyncpg.connect(
                database='lagbot',
                loop=self.loop))

    def run(self, *args, **kwargs):
        super().run(self.config.pop('bot_token'), *args, **kwargs)

    async def on_ready(self):
        self.start_time = datetime.datetime.utcnow()
        if None in (self.owner, self.client_id):
            app_info = await self.application_info()
            self.client_id = app_info.id
            self.owner = app_info.owner
            owner = OrderedDict([('name', self.owner.name),
                                 ('id', self.owner.id),
                                 ('discriminator', self.owner.discriminator),
                                 ('avatar', self.owner.avatar),
                                 ('bot', self.owner.bot)])
            config = json.load(open(self.config_file), object_pairs_hook=OrderedDict)
            config['client_id'] = self.client_id
            config['owner'] = owner
            with open(self.config_file, 'w') as fp:
                json.dump(config, fp, indent=4)
        await self.change_presence(game=discord.Game(name='Destroy All Humans!'))

    async def on_server_join(self, server):
        if self._debug:
            return
        message = 'Hello, thanks for inviting me!' \
                  '\nSay `{0.command_prefix}help` to see my commands.'
        await self.send_message(server.default_channel, message.format(self))

    async def on_message(self, msg):
        if msg.author.bot:
            return
        await self.process_commands(msg)

    def tb_args(self, exc):
        return (type(exc), exc, exc.__traceback__)

    async def on_command_error(self, exc, ctx):
        """Emulate default on_command_error and add server + channel info."""
        if hasattr(ctx.command, 'on_error') or isinstance(exc, commands.CommandNotFound):
            return
        print('Ignoring exception in command {}'.format(ctx.command),
              file=sys.stderr)
        traceback.print_exception(*self.tb_args(exc), file=sys.stderr)
        if isinstance(ctx.message.channel, discord.PrivateChannel):
            if str(ctx.message.channel.type) == 'group':
                msg = 'Message was "{0.content}" by {0.author} in {0.channel}.'
            else:
                msg = 'Message was "{0.content}" in {0.channel}.'
        else:
            msg = 'Message was "{0.content}" by {0.author} in "{0.channel}" on "{0.server}".'
        msg = msg.format(ctx.message)
        print(msg, file=sys.stderr)
        tb = traceback.format_exception(*self.tb_args(getattr(exc, 'original', exc)))
        tb = ''.join(tb)
        try:
            await self.send_message(self.owner, '{}\n```py\n{}\n```'.format(msg, tb))
        except:
            pass
