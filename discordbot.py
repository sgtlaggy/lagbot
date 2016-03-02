"""Discord bot for Discord."""

import discord
import asyncio
import logging

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
        await client.send_message(message.channel, '{}{}: {}'.format(
            com,
            ' ' * (space[ind] + 1),
            func_desc(com.func)))


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
        'test': '124369415344095234'}
    coms = {com.name: com for com in [
        Command('!commands', commands, [serv['server']])]}
    com, *args = message.content.split()
    if com in coms:
        if com == '!commands':
            await coms[com].func(message, coms)
        else:
            await coms[com].func(message, args)

if __name__ == '__main__':
    client.run(dis_name, dis_pass)
