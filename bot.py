"""Discord bot for Discord."""

from collections import OrderedDict
import datetime
import requests
import asyncio
import logging
import json
import sys
import os

from discord.ext import commands
import discord

# Files and Paths
app_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
data_path = os.path.join(app_path, 'data')
token_file = os.path.join(app_path, 'token.txt')
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

cogs = [
    'cogs.admin',
    'cogs.misc',
    'cogs.meta',
    'cogs.stream']


@bot.event
async def on_ready():
    """Called when bot is ready."""
    log.info('Bot ready!')
    bot.uptime = datetime.datetime.utcnow()
    for cog in cogs:
        try:
            bot.load_extension(cog)
        except Exception as e:
            print("Couldn't load cog {}\n{}: {}".format(
                cog, type(e).__name__, e))
    await bot.change_status(game=discord.Game(name='Destroy All Humans!'))


@bot.event
async def on_message(msg):
    """Called when message is recieved."""
    if msg.author == bot.user:
        return
    await bot.process_commands(msg)


if __name__ == '__main__':
    if any('debug' in arg.lower() for arg in sys.argv):
        bot.command_prefix = '%!'
    with open(token_file, 'r') as fp:
        token = fp.read()[:-1]
    try:
        bot.run(token)
    except Exception as e:
        print(e)
        log.error(e)
