"""Discord bot for Discord."""

from collections import OrderedDict
import discord
import asyncio
import logging
import json
import sys
import os

import creds
from command import Command

# Bot Owner Discord ID
bot_owner = '103714384802480128'

# Discord Client/Bot
client = discord.Client()

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


def can_kick_ban(msg, kb):
    """Determine whether user can kick/ban."""
    for role in msg.author.roles:
        if kb == 'kick':
            if role.permissions.kick_members:
                return True
        else:
            if role.permissions.ban_members:
                return True
    return False


def stream_name_link(nl):
    """Get stream link from name or vice-versa."""
    if nl.startswith('http://'):
        link = nl
        name = link.split('/')[-1]
    else:
        name = nl
        link = 'http://twitch.tv/{}'.format(name.lower())
    return name, link


def com_perm_check(msg, com):
    """Check if command can be used by user and on server."""
    if ((com.servers is None or msg.server.id in com.servers) and
            (com.users is None or msg.author in com.users)) \
            or msg.author.id == bot_owner:
        return True
    return False


def unformat_str(raw):
    """Make a string discord-friendly."""
    new = ''
    rep = ['_', '*', '`', '~']
    for c in raw:
        if c in rep:
            new += '\\'
        new += c
    return new


# Command functions.


async def bot_info(msg, *_):
    """Print bot information."""
    lib_link = unformat_str('https://github.com/Rapptz/discord.py/tree/async')
    source_link = unformat_str('https://github.com/mikevb1/discordbot')
    message = """This bot is written in Python using discord.py from {}
    The source code can be found at {}
    Say `!help` to see available commands.
    Say `!help command` to see how to use a command.""".format(
        lib_link, source_link)
    await client.send_message(msg.channel, message)


async def commands(msg, coms):
    """Print all commands available on server."""
    message = ''
    message += 'Available commands:\n'
    serv_coms = []
    serv_coms = [com for com in coms.values() if com_perm_check(msg, com)]
    space = list_align([com.name for com in serv_coms])
    for ind, com in enumerate(serv_coms):
        message += '`{}{}: {}`\n'.format(
            com,
            ' ' * (space[ind] + 1),
            func_desc(com.func))
    await client.send_message(msg.channel, message)


async def help_com(msg, coms, *args):
    """Print description and usage of command.

    Usage:
    !help
    !help help
    !help !help
    """
    message = ''
    try:
        com = args[0]
    except:
        await commands(msg, coms)
        return
    if not com.startswith('!'):
        com = '!' + com
    if com in coms:
        message += '`{} : {}`\n'.format(com, func_desc(coms[com].func))
        for line in coms[com].func.__doc__.splitlines()[1:-1]:
            if line:
                message += '`{}`\n'.format(line)
        await client.send_message(msg.channel, message)
    else:
        await client.send_message(
            msg.channel,
            '{} is not a valid command.'.format(args[0]))


async def emotes_com(msg, emotes):
    """Print all emotes available.

    Usage: !emotes
    """
    message = 'Available emotes:\n'
    space = list_align(emotes.keys())
    for ind, emote in enumerate(emotes.values()):
        message += '`{}{}:` {}\n'.format(
            emote.name,
            ' ' * (space[ind] + 1),
            unformat_str(repr(emote.func))[1:-1])
    await client.send_message(msg.channel, message)


async def do_emote(msg, emote):
    """Send emote, with mentions."""
    mentions = ' '.join([m.mention for m in msg.mentions])
    await client.send_message(
        msg.channel,
        '{}: {}{}'.format(msg.author.name, emote, mentions))
    try:
        await client.delete_message(msg)
    except:
        pass


async def stream_message(msg, *args):
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


async def stream(msg, *args):
    """Announce that you or someone else is streaming.

    Usage:
    !stream http://twitch.tv/sgthoppy (announce someone not in discord)
    !stream @sgtlaggy                 (announce someone else)
    !stream                           (announce yourself)
    !stream # announcement message    (announce with message, mention everyone)
    !stream $ announcement message    (announce with message, no mention)
    """
    stream_text = '{} is streaming at {}'
    if len(streamers) == 0:
        await client.send_message(msg.channel, 'No streamers have been added.')
        return
    message = await stream_message(msg, *args)
    message += stream_text
    if len(args) == 0 or args[0] in ('#', '$'):
        try:
            author = msg.author
            link = streamers[author.id]
            await client.send_message(
                msg.channel,
                message.format(author.name, link))
        except KeyError:
            await client.send_message(
                msg.channel,
                'You are not in the list of streamers.')
            pass
    elif len(msg.mentions) == 0:
        if args[0].startswith('http:'):
            name, link = stream_name_link(args[0])
            await client.send_message(
                msg.channel,
                message.format(name, link))
    else:
        for m in msg.mentions:
            try:
                await client.send_message(
                    msg.channel,
                    message.format(m.name, streamers[m.id]))
            except:
                await client.send_message(
                    msg.channel,
                    '{} is not in the list of streamers.'.format(m.name))
    try:
        await client.delete_message(msg)
    except:
        pass


async def add_stream(msg, *args):
    """Add or update a streamer's link.

    Usage:
    !addstream twitch.tv/sgthoppy           (your link)
    !addstream @sgtlaggy twitch.tv/sgthoppy (someone else's link)
    """
    global streamers
    if len(args) in (1, 2):
        try:
            name, link = msg.mentions[0].name, args[1]
            sid = msg.mentions[0].id
        except IndexError:
            name, link = msg.author.name, args[0]
            sid = msg.author.id
        except:
            await client.send_message(msg.channel, 'Try `!help addstream`.')
            return
    else:
        await client.send_message(msg.channel, 'Try `!help addstream`.')
        return
    streamers[sid] = link
    with open(stream_file, 'w') as s:
        json.dump(streamers, s)
        await client.send_message(
            msg.channel,
            'Adding {} ({}) to steamer list.'.format(name, link))


async def remove_stream(msg, *args):
    """Remove streamer from list.

    Usage:
    !remstream
    !remstream @sgtlaggy
    """
    global streamers
    if len(args) == 0:
        name, sid = msg.author.name, msg.author.id
    else:
        try:
            name, sid = msg.mentions[0].name, msg.mentions[0].id
        except:
            return
    try:
        del streamers[sid]
    except:
        await client.send_message(
            msg.channel,
            'Streamer {} does not exist in list.'.format(name))
        return
    await client.send_message(
        msg.channel,
        '{} has been removed.'.format(name))
    with open(stream_file, 'w') as s:
        json.dump(streamers, s)


async def join(msg, *args):
    """Tell bot to join server using ID or discordgg link.

    Usage:
    !join 0h4QlpGEPGkSCO6I                    (invite ID)
    !join https://discord.gg/0h4QlpGEPGkSCO6I (invite link)
    """
    try:
        await client.accept_invite(args[0])
        await client.send_message(
            msg.channel,
            'Successfully joined {}'.format(args[0]))
    except IndexError:
        pass
    except discord.HTTPException:
        await client.send_message(msg.channel, 'Could not join server.')
    except discord.NotFound:
        await client.send_message(
            msg.channel,
            'Invite is invalid or expired.')


async def leave(msg, *_):
    """Tell bot to leave server.

    Usage: !leave
    """
    if not can_kick_ban(msg, 'kick'):
        await client.send_message(
            msg.channel,
            "You can't tell me to leave.")
        return
    try:
        await client.leave_server(msg.server)
    except discord.HTTPException:
        await client.send_message(msg.channel, 'Could not leave server.')


async def kick_ban(msg, kb, days=1):
    """Kick/ban user from server."""
    if can_kick_ban(msg, kb):
        for m in msg.mentions:
            try:
                if kb == 'kick':
                    await client.kick(m)
                    kbs = 'Kicked'
                else:
                    await client.ban(m, days)
                    kbs = 'Banned'
                await client.send_message(
                    msg.channel,
                    "{} {}.".format(kbs, str(m)))
            except discord.Forbidden:
                await client.send_message(
                    msg.channel,
                    "I don't have permission to {} {}.".format(kb, str(m)))
            except discord.HTTPException:
                await client.send_message(
                    msg.channel,
                    'Failed to {} {}.'.format(kb, str(m)))
    else:
        await client.send_message(
            msg.channel,
            "You don't have permission to {} users.".format(kb))


async def kick(msg, *_):
    """Kick user from server if you have permission.

    Usage: !kick @sgtlaggy
    """
    await kick_ban(msg, 'kick')


async def ban(msg, *args):
    """Ban user from server if you have permission.

    Usage: !ban @sgtlaggy
    """
    days = 1
    try:
        days = int(args[0])
        if days > 7:
            days = 7
        elif days < 0:
            days = 0
    except KeyError:
        return
    except ValueError:
        pass
    await kick_ban(msg, 'ban', days)


# Command Setup
compre = '!'
coms_list = [
    Command(compre + 'info', bot_info),
    Command(compre + 'help', help_com),
    Command(compre + 'emotes', emotes_com),
    Command(compre + 'kick', kick),
    Command(compre + 'ban', ban),
    Command(compre + 'join', join),
    Command(compre + 'leave', leave),
    Command(compre + 'stream', stream),
    Command(compre + 'addstream', add_stream),
    Command(compre + 'remstream', remove_stream)]
coms = OrderedDict()
for com in coms_list:
    coms[com.name] = com

emote_list = [
    Command(compre + 'disapprove', 'ಠ_ಠ'),
    Command(compre + 'lenny', '( ͡° ͜ʖ ͡°)'),
    Command(compre + 'lennies', '( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)'),
    Command(compre + 'fight', '(ง ͠° ͟ل͜ ͡°)ง'),
    Command(compre + 'shrug', '¯\_(ツ)_/¯'),
    Command(compre + 'donger', 'ヽ༼ຈل͜ຈ༽ﾉ raise your dongers ヽ༼ຈل͜ຈ༽ﾉ'),
    Command(compre + 'give', '༼ つ ◕_◕ ༽つ'),
    Command(compre + 'zoidberg', '(\/) (°,,,°) (\/)'),
    Command(compre + 'ayy', ':alien: ayy lmao')]
emotes = OrderedDict()
for emote in emote_list:
    emotes[emote.name] = emote


# Discord functions.


@client.event
async def on_ready():
    """Called when bot is ready."""
    log.info('Bot ready!')
    await client.change_status(game=discord.Game(name='Destroy All Humans!'))


@client.event
async def on_message(msg):
    """Define what happens when message is recieved."""
    if msg.author == client.user:
        return
    com, *args = msg.content.split()
    if com in emotes:
        await do_emote(msg, emotes[com].func)
    elif com in coms:
        if not com_perm_check(msg, coms[com]):
            await client.send_message(
                msg.channel,
                'You cannot use that command!')
            return
        if com == '!emotes':
            await coms[com].func(msg, emotes)
        elif com == '!help':
            await coms[com].func(msg, coms, *args)
        else:
            await coms[com].func(msg, *args)

if __name__ == '__main__':
    client.run(creds.dis_name, creds.dis_pass)
