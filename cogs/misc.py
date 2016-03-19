"""Cog for miscellaneous stuff."""

from collections import OrderedDict
import datetime
import random

from discord.ext import commands
import asyncio


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


def unformat_str(raw):
    """Make a string discord-friendly."""
    new = ''
    rep = ['_', '*', '`', '~']
    for c in raw:
        if c in rep:
            new += '\\'
        new += c
    return new


class Misc:
    """Miscellaneous functions/commands and stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot
        self.temote_prefix = ';'

    @commands.command(name='help')
    async def help_cmd(self, cmd=None):
        """Print this help."""
        if cmd is None:
            coms = OrderedDict()
            com_list = [
                'help', 'info', 'emotes', 'poke',
                'stream', 'join', 'leave', 'kick', 'ban']
            space = list_align(com_list, 2)
            for com in com_list:
                coms[com] = self.bot.commands[com]
            message = ['Available commands:', '```']
            for i, com in enumerate(coms):
                message.append('{}{}: {}'.format(
                    com, ' ' * space[i], coms[com].help.splitlines()[0]))
            message.append(
                '\nTo use Twitch/BTTV emotes, prefix the emote with {}'.format(
                    self.temote_prefix))
            message.append('```')
            message = '\n'.join(message)
            await self.bot.say(message)
        else:
            try:
                message = self.bot.commands[cmd].help.format(
                    self.bot.command_prefix)
            except KeyError:
                return
            except:
                message = self.bot.commands[cmd].help
            await self.bot.say('```' + message + '```')

    @commands.command()
    async def info(self):
        """Print bot information."""
        lib_link = \
            unformat_str('https://github.com/Rapptz/discord.py/tree/async')
        source_link = unformat_str('https://github.com/mikevb1/discordbot')
        twitch_emote_link = unformat_str('https://twitchemotes.com/')
        bttv_emote_link = unformat_str('http://www.nightdev.com/betterttv/')
        message = """This bot is written in Python using discord.py from {}
        The source code can be found at {}
        Global Twitch emote functionality provided by {}
        BTTV emote functionality provided by night (see code for API) {}""". \
            format(
                lib_link, source_link, twitch_emote_link, bttv_emote_link)
        await self.bot.say(message)

    @commands.command()
    async def poke(self):
        """Make sure bot is working."""
        replies = [
            'Hey!', 'Ow!', 'Stop that!', "I'm here!", 'I need an adult!']
        await self.bot.say(random.choice(replies))

    @commands.command()
    async def uptime(self):
        """Display bot uptime."""
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            fmt = '{d} days, {h} hours, {m} minutes, {s} seconds'
        else:
            fmt = '{h} hours, {m} minutes, {s} seconds'
        up = fmt.format(d=days, h=hours, m=minutes, s=seconds)
        await self.bot.say('Uptime: **{}**'.format(up))


def setup(bot):
    """'Magic' function to set up cog."""
    bot.add_cog(Misc(bot))
