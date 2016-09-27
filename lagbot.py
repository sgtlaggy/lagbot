import traceback
import datetime
import sys

from discord.ext import commands
import discord
import aiohttp
import asyncpg


class LagBot(commands.Bot):
    def __init__(self, *args, config, debug=False, **kwargs):
        self._debug = debug
        self.config = config
        super().__init__(*args, **kwargs)
        if self._debug:
            self.command_prefix = '%!'
        self.aiohsession = aiohttp.ClientSession(
            loop=self.loop,
            headers={'User-Agent': "sgtlaggy Discord Bot/6.9"})
        self.db = self.loop.run_until_complete(
            asyncpg.connect(
                database='lagbot',
                loop=self.loop))

    def run(self, *args, **kwargs):
        super().run(self.config.pop('bot_token'), *args, **kwargs)

    async def on_ready(self):
        self.start_time = datetime.datetime.utcnow()
        app_info = await self.application_info()
        self.client_id = app_info.id
        self.owner = app_info.owner
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
