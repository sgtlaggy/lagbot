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

# Discord Client/Bot
client = discord.Client()

app_path = os.path.split(os.path.abspath(sys.argv[0]))[0]
data_path = os.path.join(app_path, 'data')
log_file = os.path.join(app_path, 'bot.log')
stream_file = os.path.join(data_path, 'stream.json')

if not os.path.isdir(data_path):
    os.mkdir(data_path)

# Logging Setup
log = logging.getLogger('discord')
log.setLevel(logging.DEBUG)
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
    if nl.startswith('http://') or nl.startswith('https://') or \
            nl.startswith('twitch.tv') or nl.startswith('hitbox.tv'):
        link = nl
        name = link.split('/')[-1]
    else:
        name = nl
        link = 'http://twitch.tv/{}'.format(name.lower())
    return name, link


def com_perm_check(msg, com):
    """Check if command can be used by user and on server."""
    if (com.servers is None or msg.server.id in com.servers) and \
            (com.users is None or msg.author in com.users):
        return True
    return False


# Command functions.


async def commands(msg, commands):
    """Print all commands available on server.

    Usage: !commands
    """
    await client.send_message(msg.channel, 'Available commands:')
    serv_coms = []
    serv_coms = [com for com in commands.values() if com_perm_check(msg, com)]
    space = list_align([com.name for com in serv_coms])
    for ind, com in enumerate(serv_coms):
        await client.send_message(msg.channel, '`{}{}: {}`'.format(
            com,
            ' ' * (space[ind] + 1),
            func_desc(com.func)))


async def help_com(msg, commands, *args):
    """Print description and usage of command.

    Usage:
    !help help
    !help !help
    """
    try:
        com = args[0]
    except:
        await client.send_message(msg.channel, 'Try `!commands`')
        return
    if not com.startswith('!'):
        com = '!' + com
    if com in commands:
        await client.send_message(
            msg.channel,
            '`{} : {}`'.format(com, func_desc(commands[com].func)))
        for line in commands[com].func.__doc__.splitlines()[1:-1]:
            if line:
                await client.send_message(
                    msg.channel,
                    '`{}`'.format(line))
    else:
        await client.send_message(msg.channel, 'Try `!commands`')


async def emotes_com(msg, emotes):
    """Print all emotes available.

    Usage: !emotes
    """
    await client.send_message(msg.channel, 'Available emotes:')
    space = list_align(emotes.keys())
    for ind, emote in enumerate(emotes.values()):
        await client.send_message(msg.channel, '`{}{}: {}`'.format(
            emote.name,
            ' ' * (space[ind] + 1),
            emote.func))


async def do_emote(msg, emote):
    """Send emote, with mentions."""
    mentions = ''
    mentions += ' '.join([m.mention for m in msg.mentions])
    await client.send_message(
        msg.channel,
        '{}{}'.format(mentions, emote))
    try:
        await client.delete_message(msg)
    except:
        pass


async def stream_message(msg, *args):
    """Get message in stream announcement."""
    if '#' in args:
        for i, a in enumerate(args):
            if a == '#':
                return '@everyone ' + ' '.join(args[i + 1:])
                break
    elif '$' in args:
        for i, a in enumerate(args):
            if a == '$':
                return ' '.join(args[i + 1:])
                break
    return ''


async def stream(msg, *args):
    """Announce that you or someone else is streaming.

    Usage:
    !stream twitch.tv/sgthoppy      (announce someone not in discord)
    !stream @sgtlaggy               (announce someone else)
    !stream                         (announce yourself)
    !stream # announcement message  (announce with a message, mention everyone)
    !stream $ announcement message  (announce with a message, no mention)
    """
    stream_text = '{} is streaming at {}'
    try:
        with open(stream_file, 'r') as s:
            streamers = json.load(s)
    except FileNotFoundError:
        await client.send_message(msg.channel, 'No streamers have been added.')
        return
    author = str(msg.author)
    message = await stream_message(msg, *args)
    if message:
        message += '\n'
    message += stream_text
    if len(args) == 0 or args[0] in ('#', '$'):
        try:
            link = streamers[author]
            await client.send_message(
                msg.channel,
                message.format(author, link))
        except KeyError:
            await client.send_message(
                msg.channel,
                'You are not in the list of streamers.')
            pass
    elif len(msg.mentions) < len(args):
        if args[0].startswith('http:') or args[0].startswith('twitch.tv'):
            name, link = stream_name_link(args[0])
            await client.send_message(
                msg.channel,
                message.format(name, link))
    else:
        for m in msg.mentions:
            try:
                await client.send_message(
                    msg.channel,
                    message.format(m.name, streamers[m.name]))
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
    !addstream                              (your link, matching name)
    !addstream twitch.tv/sgthoppy           (your link)
    !addstream @sgtlaggy twitch.tv/sgthoppy (someone else's link)
    """
    try:
        with open(stream_file, 'r') as s:
            streamers = json.load(s)
    except FileNotFoundError:
        streamers = {}
    if len(args) == 2:
        try:
            name, link = str(msg.mentions[0]), args[1]
        except:
            return
    elif len(args) == 1:
        name, link = msg.author.name, args[0]
    else:
        return
    streamers[name] = link
    with open(stream_file, 'w') as s:
        json.dump(streamers, s)
        await client.send_message(
            msg.channel,
            'Adding {} ({}) to steamer list.'.format(name, link))


async def remove_stream(msg, *args):
    """Remove streamer from list.

    Usage: !remstream @sgtlaggy
    """
    with open(stream_file, 'r') as s:
        streamers = json.load(s)
    try:
        name = str(msg.mentions[0])
    except:
        return
    try:
        del streamers[name]
    except:
        await client.send_message(
            msg.channel,
            'Streamer {} does not exist in list.'.format(args[0]))
        return
    await client.send_message(
        msg.channel,
        '{} has been removed.'.format(args[0]))
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


async def leave(msg, *args):
    """Tell bot to leave server.

    Usage: !leave
    """
    if not can_kick_ban(msg, 'kick'):
        await client.send_message(
            msg.channel,
            "You can't tell me to leave.")
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


async def kick(msg, *args):
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
coms_list = [
    Command('!commands', commands),
    Command('!help', help_com),
    Command('!emotes', emotes_com),
    Command('!kick', kick),
    Command('!ban', ban),
    Command('!join', join),
    Command('!leave', leave),
    Command('!stream', stream),
    Command('!addstream', add_stream),
    Command('!remstream', remove_stream)]
coms = OrderedDict()
for com in coms_list:
    coms[com.name] = com

emote_list = [
    Command('!disapprove', 'ಠ_ಠ'),
    Command('!lenny', '( ͡° ͜ʖ ͡°)'),
    Command('!lennies', '( ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)'),
    Command('!fight', '(ง ͠° ͟ل͜ ͡°)ง'),
    Command('!shrug', '¯\\_(ツ)_/¯'),
    Command('!donger', 'ヽ༼ຈل͜ຈ༽ﾉ raise your dongers ヽ༼ຈل͜ຈ༽ﾉ'),
    Command('!give', '༼ つ ◕_◕ ༽つ'),
    Command('!zoidberg', '(\\\/) (°,,,°) (\\\/)')]
emotes = OrderedDict()
for emote in emote_list:
    emotes[emote.name] = emote


# Discord functions.


@client.event
async def on_ready():
    """Called when bot is ready."""
    log.info('Bot ready!')


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
        if com == '!commands':
            await coms[com].func(msg, coms)
        elif com == '!emotes':
            await coms[com].func(msg, emotes)
        elif com == '!help':
            await coms[com].func(msg, coms, *args)
        else:
            await coms[com].func(msg, *args)

if __name__ == '__main__':
    client.run(creds.dis_name, creds.dis_pass)
