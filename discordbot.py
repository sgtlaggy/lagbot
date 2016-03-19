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
import creds

# Files and Paths
app_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
data_path = os.path.join(app_path, 'data')
log_file = os.path.join(app_path, 'bot.log')
if not os.path.isdir(data_path):
    os.mkdir(data_path)

# Logging Setup
log = logging.getLogger('discord')
log.setLevel(logging.INFO)
fhandler = logging.FileHandler(
    filename=log_file,
    encoding='utf-8',
    mode='a')
fhandler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
log.addHandler(fhandler)

# Discord Client/Bot
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')

cogs = [
    'cogs.admin',
    'cogs.misc',
    'cogs.stream']

# Emote Stuff
emote_prefix = ':'
text_emotes = OrderedDict([
    ("disapprove", "ಠ_ಠ"),
    ("lenny", "( ͡° ͜ʖ ͡°)"),
    ("highlenny", "( ͡⊙ ͜ʖ ͡⊙)"),
    ("lennies", "( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)"),
    ("fight", "(ง ͠° ͟ل͜ ͡°)ง"),
    ("shrug", "¯\\_(ツ)_/¯"),
    ("donger", "ヽ༼ຈل͜ຈ༽ﾉ raise your dongers ヽ༼ຈل͜ຈ༽ﾉ"),
    ("give", "༼ つ ◕_◕ ༽つ"),
    ("zoidberg", "(\\/) (°,,,°) (\\/)"),
    ("ayy", ":alien: ayy lmao")])

emote_path = os.path.join(data_path, 'emotes')
emote_image = os.path.join(emote_path, '{}.png')
if not os.path.isdir(emote_path):
    os.mkdir(emote_path)
temote_prefix = ';'
temote_api = "https://twitchemotes.com/api_cache/v2/global.json"
temote_file = os.path.join(data_path, 'temotes.json')
temotes = {}
bemote_api = "https://api.betterttv.net/2/emotes"
bemote_file = os.path.join(data_path, 'bemotes.json')
bemotes = {}


def update_emotes(site=None):
    """Update Twitch/BTTV emotes."""
    global temotes
    global bemotes
    if site is None or site[0].lower() == 't':
        with open(temote_file, 'w') as fp:
            temotes = requests.get(temote_api).json()
            temotes['emotes'] = {e.lower(): temotes['emotes'][e]['image_id']
                                 for e in temotes['emotes']}
            json.dump(temotes, fp)
    if site is None or site[0].lower() == 'b':
        with open(bemote_file, 'w') as fp:
            bemotes = requests.get(bemote_api).json()
            bemotes['emotes'] = {e['code'].lower(): e['id']
                                 for e in bemotes['emotes']}
            bemotes['urlTemplate'] = 'http:' + bemotes['urlTemplate'].replace(
                '{{id}}', '{image_id}').replace('{{image}}', '1x')
            bemotes['time'] = datetime.datetime.utcnow().strftime(
                '%Y-%m-%dT%H:%M%SZ')
            json.dump(bemotes, fp)

try:
    with open(temote_file, 'r') as fp:
        temotes = json.load(fp)
    if datetime.datetime.strptime(
            temotes['meta']['generated_at'],
            '%Y-%m-%dT%H:%M:%SZ') + datetime.timedelta(days=1) < \
            datetime.datetime.utcnow():
        raise Exception
except:
    update_emotes('t')
try:
    with open(bemote_file, 'r') as fp:
        bemotes = json.load(fp)
    if datetime.datetime.strptime(
            bemotes['time'], '%Y-%m-%dT%H:%M:%SZ') \
            + datetime.timedelta(days=1) < datetime.datetime.utcnow():
        raise Exception
except:
    update_emotes('b')


@bot.group(pass_context=True, invoke_without_commands=True)
async def emotes(ctx):
    """Print all emotes available."""
    if ctx.invoked_subcommand is None:
        message = ['Available emotes:']
        space = list_align(text_emotes.keys(), 1)
        for i, emote in enumerate(text_emotes):
            message.append('`{}{}{}:` {}'.format(
                emote_prefix,
                emote,
                ' ' * space[i],
                unformat_str(repr(text_emotes[emote]))[1:-1]))
        message = '\n'.join(message)
        await bot.say(message)


@emotes.command(name='update')
async def emotes_update(site=None):
    """Update Twitch/BTTV emotes."""
    update_emotes(site)


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
    global temotes
    msg_lower = msg.content.lower().split()
    if emote_prefix in msg.content:
        emote = False
        message = [msg.author.name + ':']
        for word in msg_lower:
            if emote_prefix in word:
                try:
                    message.append(
                        text_emotes[word.split(emote_prefix)[1]])
                    emote = True
                    continue
                except:
                    pass
            message.append(word)
        if emote:
            mentions = ' '.join([m.mention for m in msg.mentions])
            message.append(mentions)
            message = ' '.join(message)
            await bot.send_message(msg.channel, message)
            try:
                await bot.delete_message(msg)
            except:
                pass
    if temote_prefix in msg.content:
        ids = []
        for word in msg_lower:
            if temote_prefix in word:
                try:
                    ids.append(temotes['emotes']
                               [word.split(temote_prefix)[1].lower()])
                except KeyError:
                    try:
                        ids.append(bemotes['emotes']
                                   [word.split(temote_prefix)[1].lower()])
                    except KeyError:
                        pass
        if len(ids) == len(msg.content.split()):
            try:
                await bot.delete_message(msg)
            except:
                pass
        for image_id in ids:
            try:
                with open(emote_image.format(image_id), 'rb') as fp:
                    await bot.send_file(msg.channel, fp)
            except FileNotFoundError:
                image = requests.get(temotes['template']['small'].format(
                    image_id=image_id))
                if '404' in str(image):
                    image = requests.get(bemotes['urlTemplate'].format(
                        image_id=image_id))
                with open(emote_image.format(image_id), 'wb') as fp:
                    fp.write(image.content)
                with open(emote_image.format(image_id), 'rb') as fp:
                    await bot.send_file(msg.channel, fp)
            except:
                pass
    await bot.process_commands(msg)


if __name__ == '__main__':
    if any('debug' in arg.lower() for arg in sys.argv):
        bot.command_prefix = '%!'
    bot.run(creds.dis_name, creds.dis_pass)
