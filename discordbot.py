"""Discord bot for Discord."""

from collections import OrderedDict
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

app_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
data_path = os.path.join(app_path, 'data')
log_file = os.path.join(app_path, 'bot.log')
stream_file = os.path.join(data_path, 'stream.json')

try:
    with open(stream_file, 'r') as fp:
        streamers = json.load(fp)
except:
    streamers = {}

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


def list_align(words):
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


@bot.command()
async def info():
    """Print bot information."""
    lib_link = unformat_str('https://github.com/Rapptz/discord.py/tree/async')
    source_link = unformat_str('https://github.com/mikevb1/discordbot')
    message = """This bot is written in Python using discord.py from {}
    The source code can be found at {}""".format(lib_link, source_link)
    await bot.say(message)


@bot.command(name='emotes')
async def emotes_com():
    """Print all emotes available."""
    message = 'Available emotes:\n'
    space = list_align(emotes.keys())
    for i, emote in enumerate(emotes):
        message += '`{}{}:` {}\n'.format(
            emote,
            ' ' * (space[i] + 1),
            unformat_str(repr(emotes[emote]))[1:-1])
    await bot.say(message)


@bot.command(aliases=emotes.keys(), pass_context=True)
async def do_emote(ctx):
    """Send emote, with mentions."""
    emote = emotes[ctx.invoked_with]
    mentions = ' '.join([m.mention for m in ctx.message.mentions])
    await bot.say('{}: {} {}'.format(ctx.message.author.name, emote, mentions))
    try:
        await bot.delete_message(ctx.message)
    except:
        pass


@bot.command()
async def poke():
    """Make sure bot is working."""
    replies = ['Hey!', 'Ow!', 'Stop that!', "I'm here!", 'I need an adult!']
    await bot.say(random.choice(replies))


@bot.group(pass_context=True, invoke_without_command=True)
async def stream(ctx, *args):
    """Announce that you or someone else is streaming.

    Usage:
    !stream http://twitch.tv/user  (announce someone not in discord)
    !stream @user                  (announce someone else)
    !stream                        (announce yourself)
    !stream # announcement message (announce with message, mention everyone)
    !stream $ announcement message (announce with message, no mention)
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
    !stream add @user http://twitch.tv/user
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
    !stream rem @user
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
    """Tell bot to join server using ID or discordgg link.

    Usage:
    !join 0h4QlpGEPGkSCO6I                    (invite ID)
    !join https://discord.gg/0h4QlpGEPGkSCO6I (invite link)
    """
    try:
        await bot.accept_invite(channel)
    except:
        pass


@bot.command(pass_context=True)
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def leave(ctx):
    """Tell bot to leave server.

    Usage: !leave
    """
    await bot.leave_server(ctx.message.server)


@bot.command(pass_context=True)
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick(ctx):
    """Kick user from server if you have permission.

    Usage:
    !kick @user
    """
    for m in ctx.message.mentions:
        await bot.kick(m)


@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban(member, days=1):
    """Ban user from server if you have permission.

    Usage:
    !ban @user
    """
    days = int(days)
    if days > 7:
        days = 7
    elif days < 0:
        days = 0
    await bot.ban(member, days)


@bot.event
async def on_ready():
    """Called when bot is ready."""
    log.info('Bot ready!')
    await bot.change_status(game=discord.Game(name='Destroy All Humans!'))


if __name__ == '__main__':
    bot.run(creds.dis_name, creds.dis_pass)
