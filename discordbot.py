"""Discord bot for Discord."""

from collections import OrderedDict
import datetime
import requests
import asyncio
import logging
import random
import json
import sys
import os

from discord.ext import commands
import discord
import creds

# Bot Owner Discord ID
bot_owner = '103714384802480128'

# Discord Client/Bot
bot = commands.Bot(command_prefix='!')
bot.remove_command('help')

# Files and Paths
app_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
data_path = os.path.join(app_path, 'data')
log_file = os.path.join(app_path, 'bot.log')

stream_file = os.path.join(data_path, 'stream.json')
try:
    with open(stream_file, 'r') as fp:
        streamers = json.load(fp)
except:
    streamers = {}

emote_image = os.path.join(data_path, 'emote.png')
emote_prefix = ':'
temote_prefix = ';'
temote_api = "https://twitchemotes.com/api_cache/v2/global.json"
temote_file = os.path.join(data_path, 'temotes.json')
try:
    with open(temote_file, 'r') as fp:
        temotes = json.load(fp)
    if datetime.datetime.strptime(
            temotes['meta']['generated_at'],
            '%Y-%m-%dT%H:%M:%SZ') + datetime.timedelta(days=7) < \
            datetime.datetime.utcnow():
        raise Exception
except:
    with open(temote_file, 'w') as fp:
        temotes = requests.get(temote_api).json()
        temotes['emotes'] = {e.lower(): temotes['emotes'][e]['image_id']
                             for e in temotes['emotes']}
        json.dump(temotes, fp)

bemote_api = "https://api.betterttv.net/2/emotes"
bemote_file = os.path.join(data_path, 'bemotes.json')
try:
    with open(bemote_file, 'r') as fp:
        bemotes = json.load(fp)
    if datetime.datetime.strptime(
            bemotes['time'], '%Y-%m-%dT%H:%M:%SZ') \
            + datetime.timedelta(days=7) < datetime.datetime.utcnow():
        raise Exception
except:
    with open(bemote_file, 'w') as fp:
        bemotes = requests.get(bemote_api).json()
        bemotes['emotes'] = {e['code'].lower(): e['id']
                             for e in bemotes['emotes']}
        bemotes['urlTemplate'] = 'http:' + bemotes['urlTemplate'].replace(
            '{{id}}', '{image_id}').replace('{{image}}', '1x')
        bemotes['time'] = datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M%SZ')
        json.dump(bemotes, fp)

if not os.path.isdir(data_path):
    os.mkdir(data_path)

emotes = OrderedDict([
    ('disapprove', 'ಠ_ಠ'),
    ('lenny', '( ͡° ͜ʖ ͡°)'),
    ('lennies', '( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)'),
    ('fight', '(ง ͠° ͟ل͜ ͡°)ง'),
    ('shrug', '¯\_(ツ)_/¯'),
    ('donger', 'ヽ༼ຈل͜ຈ༽ﾉ raise your dongers ヽ༼ຈل͜ຈ༽ﾉ'),
    ('give', '༼ つ ◕_◕ ༽つ'),
    ('zoidberg', '(\/) (°,,,°) (\/)'),
    ('ayy', ':alien: ayy lmao')])

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


# General helper functions.


def func_desc(func):
    """Get first sentence/description of function from docstring.

    Arguments:
    func -- function to get description from

    Returns:
    str -- "No description." or first sentence of docstring
    """
    doc = func.__doc__
    if doc is None:
        return 'No description.'
    desc = ''
    for c in doc:
        if c == '\n':
            desc += ' '
        desc += c
        if c == '.':
            break
    return desc


def list_align(words, extra=0):
    """Find word of greatest length and return list of differences in length.

    Arguments:
    words -- list of words

    Returns:
    lens -- list of ints
    """
    longest = 0
    lens = []
    for word in words:
        if len(word) > longest:
            longest = len(word)
    for word in words:
        lens.append(longest - len(word))
    lens = [space + extra for space in lens]
    return lens


def is_url(text):
    """Check if a string is a standard http(s) URL."""
    if text.startswith('http:') or text.startswith('https:'):
        return True
    return False


def stream_name_link(nl):
    """Get stream link from name or vice-versa."""
    if is_url(nl):
        link = nl
        name = link.split('/')[-1]
    else:
        name = nl
        link = 'http://twitch.tv/{}'.format(name.lower())
    return name, link


def unformat_str(raw):
    """Make a string discord-friendly."""
    new = ''
    rep = ['_', '*', '`', '~']
    for c in raw:
        if c in rep:
            new += '\\'
        new += c
    return new


def stream_message(*args):
    """Get message in stream announcement."""
    message = ''
    if '#' in args:
        for i, a in enumerate(args):
            if a == '#':
                message = '@everyone ' + ' '.join(args[i + 1:])
                break
    elif '$' in args:
        for i, a in enumerate(args):
            if a == '$':
                message = ' '.join(args[i + 1:])
                break
    if message:
        message += '\n'
    return message


@bot.command(name='help')
async def help_cmd(cmd=None):
    """Print this help."""
    if cmd is None:
        coms = OrderedDict()
        com_list = [
            'help', 'info', 'emotes', 'poke',
            'stream', 'join', 'leave', 'kick', 'ban']
        space = list_align(com_list, 2)
        for com in com_list:
            coms[com] = bot.commands[com]
        message = ['Available commands:', '```']
        for i, com in enumerate(coms):
            message.append('{}{}: {}'.format(
                com, ' ' * space[i], coms[com].help.splitlines()[0]))
        message.append(
            '\nTo use Twitch/BTTV emotes, prefix the emote with {}'.format(
                temote_prefix))
        message.append('```')
        message = '\n'.join(message)
        await bot.say(message)
    else:
        try:
            message = bot.commands[cmd].help.format(bot.command_prefix)
        except KeyError:
            return
        except:
            message = bot.command[cmd].help
        await bot.say('```' + message + '```')


@bot.command()
async def info():
    """Print bot information."""
    lib_link = unformat_str('https://github.com/Rapptz/discord.py/tree/async')
    source_link = unformat_str('https://github.com/mikevb1/discordbot')
    twitch_emote_link = unformat_str('https://twitchemotes.com/')
    bttv_emote_link = unformat_str('http://www.nightdev.com/betterttv/')
    message = """This bot is written in Python using discord.py from {}
    The source code can be found at {}
    Global Twitch emote functionality provided by {}
    BTTV emote functionality provided by night (see code for API) {}""".format(
        lib_link, source_link, twitch_emote_link, bttv_emote_link)
    await bot.say(message)


@bot.command(name='emotes')
async def emotes_com():
    """Print all emotes available."""
    message = ['Available emotes:']
    space = list_align(emotes.keys(), 1)
    for i, emote in enumerate(emotes):
        message.append('`{}{}{}:` {}'.format(
            emote_prefix,
            emote,
            ' ' * space[i],
            unformat_str(repr(emotes[emote]))[1:-1]))
    message = '\n'.join(message)
    await bot.say(message)


@bot.command()
async def poke():
    """Make sure bot is working."""
    replies = ['Hey!', 'Ow!', 'Stop that!', "I'm here!", 'I need an adult!']
    await bot.say(random.choice(replies))


@bot.group(pass_context=True, invoke_without_command=True)
async def stream(ctx, *args):
    """Announce that you or someone else is streaming.

    Usage:
    {0}stream link                   (announce someone not in discord)
    {0}stream @user                  (announce someone else)
    {0}stream                        (announce yourself)
    {0}stream # announcement message (announce with message, mention everyone)
    {0}stream $ announcement message (announce with message, no mention)
    {0}stream add @user link         (add someone to list)
    {0}stream rem @user              (remove someone from list)
    """
    if ctx.invoked_subcommand is None:
        stream_text = '{} is streaming at {}'
        msg = ctx.message
        message = stream_message(args)
        message += stream_text
        if len(args) == 0 or args[0] in ('#', '$'):
            try:
                author = msg.author
                link = streamers[author.id]
                await bot.say(message.format(author.name, link))
            except KeyError:
                await bot.say('You are not in the list of streamers.')
        elif len(msg.mentions) == 0:
            name, link = stream_name_link(args[0])
            await bot.say(message.format(name, link))
        else:
            for m in msg.mentions:
                try:
                    await bot.say(message.format(m.name, streamers[m.id]))
                except:
                    await bot.say('{} is not in the list of streamers.'.format(
                        m.name))
        try:
            await bot.delete_message(msg)
        except:
            pass


@stream.command(name='add', pass_context=True)
async def add_stream(ctx, _, link):
    """Add or update a streamer's link.

    Usage:
    {0}stream add @user link
    """
    global streamers
    member = ctx.message.mentions[0]
    try:
        name, link = member.name, link
        sid = member.id
    except:
        return
    streamers[sid] = link
    with open(stream_file, 'w') as s:
        json.dump(streamers, s)
    await bot.say('Added {} ({}) to steamer list.'.format(name, link))


@stream.command(name='remove', aliases=['rem'], pass_context=True)
async def remove_stream(ctx, _):
    """Remove streamer from list.

    Usage:
    {0}stream rem @user
    """
    global streamers
    member = ctx.message.mentions[0]
    try:
        name, sid = member.name, member.id
    except:
        return
    try:
        del streamers[sid]
    except:
        return
    with open(stream_file, 'w') as s:
        json.dump(streamers, s)
    await bot.say('{} has been removed.'.format(name))


@bot.command()
async def join(channel):
    """Tell bot to join server using ID or discord.gg link.

    Usage:
    {0}join 0h4QlpGEPGkSCO6I                    (invite ID)
    {0}join https://discord.gg/0h4QlpGEPGkSCO6I (invite link)
    """
    try:
        await bot.accept_invite(channel)
    except:
        pass


@bot.command(pass_context=True)
@commands.has_permissions(kick_members=True)
async def leave(ctx):
    """Tell bot to leave server.

    Usage:
    {0}leave
    """
    await bot.leave_server(ctx.message.server)


@bot.command(pass_context=True)
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx):
    """Kick user from server if you have permission.

    Usage:
    {0}kick @user
    """
    for m in ctx.message.mentions:
        await bot.kick(m)


@bot.command(pass_context=True)
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(ctx, _, days=1):
    """Ban user from server if you have permission.

    Usage:
    {0}ban @user
    """
    days = int(days)
    if days > 7:
        days = 7
    elif days < 0:
        days = 0
    await bot.ban(ctx.message.mentions[0], days)


@bot.event
async def on_ready():
    """Called when bot is ready."""
    log.info('Bot ready!')
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
                    message.append(emotes[word.split(emote_prefix)[1]])
                    emote = True
                    continue
                except:
                    pass
            message.append(word)
        if not emote:
            return
        mentions = ' '.join([m.mention for m in msg.mentions])
        message.append(mentions)
        message = ' '.join(message)
        await bot.send_message(msg.channel, message)
        try:
            await bot.delete_message(msg)
        except:
            pass
    if temote_prefix in msg.content:
        tids = []
        bids = []
        for word in msg_lower:
            if temote_prefix in word:
                try:
                    tids.append(temotes['emotes']
                                [word.split(temote_prefix)[1].lower()])
                except KeyError:
                    try:
                        bids.append(bemotes['emotes']
                                    [word.split(temote_prefix)[1].lower()])
                    except KeyError:
                        pass
        for image_id in tids:
            image = requests.get(temotes['template']['small'].format(
                image_id=image_id)).content
            with open(emote_image, 'wb') as fp:
                fp.write(image)
            with open(emote_image, 'rb') as fp:
                await bot.send_file(msg.channel, fp)
        for image_id in bids:
            image = requests.get(bemotes['urlTemplate'].format(
                image_id=image_id)).content
            with open(emote_image, 'wb') as fp:
                fp.write(image)
            with open(emote_image, 'rb') as fp:
                await bot.send_file(msg.channel, fp)
    await bot.process_commands(msg)


if __name__ == '__main__':
    bot.run(creds.dis_name, creds.dis_pass)
