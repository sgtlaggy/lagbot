import traceback
import datetime
import asyncio
import json
import sys
import os

from discord.ext import commands
import discord
import aiohttp
import asyncpg

from cogs.utils import checks

# Files and Paths
app_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
config_file = os.path.join(app_path, 'config.json')

# Discord Client/Bot
command_prefix = '!'
help_attrs = {'hidden': True}
initial_cogs = ['cogs.{}'.format(cog) for cog in [
    'admin', 'misc', 'meta', 'rdanny', 'overwatch']]


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
        if self._debug:
            game = 'Probe All Humans!'
        else:
            game = 'Destroy All Humans!'
        await self.change_status(game=discord.Game(name=game))

    async def on_server_join(self, server):
        if self._debug:
            return
        message = 'Hello, thanks for inviting me!' \
                  '\nSay `{0.command_prefix}help` to see my commands.'
        await self.send_message(server.default_channel, message.format(bot))

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


class CogManagement:
    def __init__(self, bot):
        self.bot = bot

    async def reload_ext_helper(self, ext):
        try:
            self.bot.unload_extension('cogs.{}'.format(ext))
            self.bot.load_extension('cogs.{}'.format(ext))
        except:
            await self.bot.say("Couldn't reload cog {}.".format(ext))

    @commands.command(name='cogs', hidden=True)
    @checks.is_owner()
    async def list_exts(self):
        exts = sorted(self.bot.extensions.keys())
        message = '\n'.join(['```', 'Loaded extensions:', *exts, '```'])
        await self.bot.say(message)

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    @checks.is_owner()
    async def reload_ext(self, ext):
        mod = 'cogs.' + ext
        if mod not in self.bot.extensions:
            await self.bot.say('Cog {} is not loaded.'.format(ext))
            return
        try:
            await self.reload_ext_helper(ext)
            await self.bot.say('Reloaded cog {}.'.format(ext))
        except Exception as e:
            await self.bot.say("Couldn't reload cog {}.".format(ext))
            print(e)

    @reload_ext.command(name='all')
    @checks.is_owner()
    async def reload_all_exts(self):
        exts = [e.split('.')[1] for e in self.bot.extensions.keys()]
        await asyncio.gather(*[self.reload_ext_helper(ext) for ext in exts])
        await self.bot.say('Reloaded all cogs.')

    @commands.command(name='load', hidden=True)
    @checks.is_owner()
    async def load_ext(self, ext):
        mod = 'cogs.' + ext
        if mod in self.bot.extensions:
            await self.bot.say('Cog {} is already loaded.'.format(ext))
            return
        try:
            self.bot.load_extension(mod)
            await self.bot.say('Loaded cog {}.'.format(ext))
        except Exception as e:
            await self.bot.say("Couldn't load cog {}.".format(ext))
            print(e)

    @commands.command(name='unload', hidden=True)
    @checks.is_owner()
    async def unload_ext(self, ext):
        mod = 'cogs.' + ext
        if mod not in self.bot.extensions:
            await self.bot.say('Cog {} is not loaded.'.format(ext))
            return
        try:
            self.bot.unload_extension(mod)
            await self.bot.say('Unloaded cog {}.'.format(ext))
        except Exception as e:
            await self.bot.say("Couldn't unload cog {}.".format(ext))
            print(e)


if __name__ == '__main__':
    with open(config_file) as fp:
        config = json.load(fp)
    bot = LagBot(command_prefix=command_prefix,
                 help_attrs=help_attrs,
                 config=config,
                 debug=any('debug' in arg.lower() for arg in sys.argv))
    bot.add_cog(CogManagement(bot))

    for cog in initial_cogs:
        try:
            bot.load_extension(cog)
        except Exception as e:
            print("Couldn't load cog {}\n{}: {}".format(
                cog, type(e).__name__, e))

    try:
        bot.run()
    except Exception as e:
        print("""
        ******************************
        ***BOT CRASHED OR SOMETHING***
        ******************************""")
        print(e)
