import traceback
import datetime
import logging
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
log_file = os.path.join(app_path, 'bot.log')
config_file = os.path.join(app_path, 'config.json')

# Logging Setup
log = logging.getLogger('discord')
log.setLevel(logging.INFO)
fhandler = logging.FileHandler(
    filename=log_file,
    encoding='utf-8',
    mode='w')
fhandler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
log.addHandler(fhandler)

# Discord Client/Bot
help_attrs = {
    'hidden': True,
    'aliases': ['commands']
}
bot = commands.Bot(command_prefix='!', help_attrs=help_attrs)

cogs = ['cogs.{}'.format(cog) for cog in ['admin', 'misc', 'meta',
                                          'rdanny', 'overwatch']]


@bot.event
async def on_ready():
    bot.start_time = datetime.datetime.utcnow()
    app_info = await bot.application_info()
    bot.client_id = app_info.id
    bot.owner = app_info.owner
    await bot.change_status(game=discord.Game(name='Destroy All Humans!'))
    log.info('Bot ready!')


@bot.event
async def on_server_join(server):
    message = 'Hello, thanks for inviting me!' \
              '\nSay `{0.command_prefix}help` to see my commands.'.format(bot)
    await bot.send_message(server.default_channel, message)


@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    await bot.process_commands(msg)


@bot.event
async def on_command_error(exc, ctx):
    """Emulate default on_command_error and add server + channel info."""
    if hasattr(ctx.command, 'on_error'):
        return
    print('Ignoring exception in command {}'.format(ctx.command),
          file=sys.stderr)
    traceback.print_exception(type(exc), exc, exc.__traceback__,
                              file=sys.stderr)
    if hasattr(exc, 'original'):
        traceback.print_exception(type(exc.original), exc.original,
                                  exc.original.__traceback__, file=sys.stderr)
    print('In "{0.channel}" on "{0.server}".'
          'Message was "{0.content}"'.format(ctx.message),
          file=sys.stderr)


async def reload_ext_helper(ext):
    try:
        bot.unload_extension('cogs.{}'.format(ext))
        bot.load_extension('cogs.{}'.format(ext))
    except:
        await bot.say("Couldn't reload cog {}.".format(ext))


@bot.command(name='cogs', hidden=True)
@checks.is_owner()
async def list_exts():
    exts = sorted(bot.extensions.keys())
    message = '\n'.join(['```', 'Loaded extensions:', *exts, '```'])
    await bot.say(message)


@bot.group(name='reload', hidden=True, invoke_without_command=True)
@checks.is_owner()
async def reload_ext(ext):
    mod = 'cogs.' + ext
    if mod not in bot.extensions:
        await bot.say('Cog {} is not loaded.'.format(ext))
        return
    try:
        await reload_ext_helper(ext)
        await bot.say('Reloaded cog {}.'.format(ext))
    except Exception as e:
        await bot.say("Couldn't reload cog {}.".format(ext))
        print(e)


@reload_ext.command(name='all')
@checks.is_owner()
async def reload_all_exts():
    exts = [e.split('.')[1] for e in bot.extensions.keys()]
    for ext in exts:
        await reload_ext_helper(ext)
    await bot.say('Reloaded all cogs.')


@bot.command(name='load', hidden=True)
@checks.is_owner()
async def load_ext(ext):
    mod = 'cogs.' + ext
    if mod in bot.extensions:
        await bot.say('Cog {} is already loaded.'.format(ext))
        return
    try:
        bot.load_extension(mod)
        await bot.say('Loaded cog {}.'.format(ext))
    except Exception as e:
        await bot.say("Couldn't load cog {}.".format(ext))
        print(e)


@bot.command(name='unload', hidden=True)
@checks.is_owner()
async def unload_ext(ext):
    mod = 'cogs.' + ext
    if mod not in bot.extensions:
        await bot.say('Cog {} is not loaded.'.format(ext))
        return
    try:
        bot.unload_extension(mod)
        await bot.say('Unloaded cog {}.'.format(ext))
    except Exception as e:
        await bot.say("Couldn't unload cog {}.".format(ext))
        print(e)


if __name__ == '__main__':
    if any('debug' in arg.lower() for arg in sys.argv):
        bot.command_prefix = '%!'

    with open(config_file) as fp:
        config = json.load(fp)
    token = config.pop('bot_token', None)
    bot.source = config.pop('source', None)
    bot.userdocs = config.pop('userdocs', None)
    bot.db = bot.loop.run_until_complete(asyncpg.connect(database='lagbot',
                                                         loop=bot.loop))
    bot.aiohsession = aiohttp.ClientSession(loop=bot.loop, headers={
        'User-Agent': "sgtlaggy Discord Bot/6.9"})

    for cog in cogs:
        try:
            bot.load_extension(cog)
        except Exception as e:
            print("Couldn't load cog {}\n{}: {}".format(
                cog, type(e).__name__, e))

    try:
        bot.run(token)
    except Exception as e:
        print(e)
        log.error(e)
