"""Discord bot for Discord."""

import discord
import asyncio
import logging
import json
from collections import OrderedDict

from creds import dis_name, dis_pass
from command import Command

client = discord.Client()

log = logging.getLogger('discord')
log.setLevel(logging.INFO)
fhandler = logging.FileHandler(
    filename='discordbot.log',
    encoding='utf-8',
    mode='w')
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


# Command functions.


async def commands(message, commands):
    """Print all commands available on server.

    Arguments:
    message -- discord.Message, to get server and channel
    commands -- command dict
    """
    await client.send_message(message.channel, 'Available commands:')
    serv_coms = [
        com for com in commands.values()
        if message.server.id in com.serv]
    space = list_align([com.name for com in serv_coms])
    for ind, com in enumerate(serv_coms):
        await client.send_message(message.channel, '`{}{}: {}`'.format(
            com,
            ' ' * (space[ind] + 1),
            func_desc(com.func)))
    return


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


async def stream(message, *args):
    """Announce that you or someone else is streaming.

    Examples:
    !stream sgtlaggy -- sgtlaggy is streaming at http://twitch.tv/sgthoppy
    !stream -- YourName is streaming at http://twitch.tv/YourName
    """
    with open('stream.json', 'r') as s:
        streamers = json.load(s)
    author = str(message.author)
    if len(args) == 0:
        try:
            link = streamers[author]
            await client.send_message(
                message.channel,
                '{} is going live over at {}'.format(author, link))
        except KeyError:
            pass
    else:
        name, link = stream_name_link(args[0])
        if name in streamers:
            link = streamers[name]
        await client.send_message(
            message.channel,
            '{} is streaming over at {}'.format(name, link))


async def add_stream(message, *args):
    """Add or update a streamer's link."""
    try:
        with open('stream.json', 'r') as s:
            streamers = json.load(s)
    except FileNotFoundError:
        streamers = {}
    if len(args) == 1:
        name, link = str(message.author), args[0]
    else:
        name, link = args
    streamers[name] = link
    with open('stream.json', 'w') as s:
        json.dump(streamers, s)
        await client.send_message(
            message.channel,
            'Adding {} ({}) to steamer list.'.format(name, link))


async def remove_stream(message, *args):
    """Remove streamer from list."""
    with open('stream.json', 'r') as s:
        streamers = json.load(s)
    try:
        del streamers[args[0]]
    except:
        await client.send_message(
            message.channel,
            'Streamer {} does not exist in list.'.format(args[0]))
        return
    await client.send_message(
        message.channel,
        '{} has been removed.'.format(args[0]))
    with open('stream.json', 'w') as s:
        json.dump(streamers, s)


# Discord functions.


@client.event
async def on_ready():
    """Called when bot is ready."""
    log.info('Bot ready!')


@client.event
async def on_message(message):
    """Define what happens when message is recieved.

    command dict is structured as
    {com_name: Command(), com_name: Command()}
    where action is a function
    """
    if message.author == client.user:
        return
    serv = {
        'test': '124369415344095234',
        'tccn': '126440582619856896'}
    coms = OrderedDict()
    coms_list = [
        Command('!commands', commands, serv),
        Command('!stream', stream, serv),
        Command('!addstream', add_stream, serv),
        Command('!remstream', remove_stream, serv)]
    for com in coms_list:
        coms[com.name] = com
    com, *args = message.content.split()
    if com in coms:
        if com == '!commands':
            await coms[com].func(message, coms)
        else:
            await coms[com].func(message, *args)

if __name__ == '__main__':
    client.run(dis_name, dis_pass)
