import datetime
import logging
import json
import sys
import os

from discord.ext import commands
import discord

# Files and Paths
app_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
data_path = os.path.join(app_path, 'data')
config_file = os.path.join(app_path, 'config.json')
log_file = os.path.join(app_path, 'bot.log')
if not os.path.isdir(data_path):
    os.mkdir(data_path)

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
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')

cogs = ['cogs.{}'.format(cog) for cog in ['admin', 'misc', 'meta', 'repl']]


@bot.event
async def on_ready():
    bot.uptime = datetime.datetime.utcnow()
    for cog in cogs:
        try:
            bot.load_extension(cog)
        except Exception as e:
            print("Couldn't load cog {}\n{}: {}".format(
                cog, type(e).__name__, e))
    app_info = await bot.application_info()
    bot.client_id = app_info.id
    await bot.change_status(game=discord.Game(name='Destroy All Humans!'))
    log.info('Bot ready!')


@bot.event
async def on_server_join(server):
    message = ['Hello, thanks for inviting me!',
               'Say `{}help` to see my commands.'.format(bot.command_prefix)]
    message = '\n'.join(message)
    for ch in server.channels:
        if ch.name == 'general' or ch.topic and 'general' in ch.topic:
            await bot.send_message(ch, message)
            return


@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    await bot.process_commands(msg)


def load_config():
    with open(config_file, 'r') as fp:
        config = json.load(fp)
    return config


if __name__ == '__main__':
    if any('debug' in arg.lower() for arg in sys.argv):
        bot.command_prefix = '%!'
    config = load_config()
    bot.owner_name = config.pop('owner_name', None)
    token = config.pop('bot_token', None)
    try:
        bot.run(token)
    except Exception as e:
        print(e)
        log.error(e)
