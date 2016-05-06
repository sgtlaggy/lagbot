"""Cog for meta/bot stuff."""

from collections import OrderedDict
import datetime
import random

from discord.ext import commands
import asyncio

from .utils import list_align


class Meta:
    """Meta/bot stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot

    @commands.command(name='help')
    async def help_cmd(self, cmd=None):
        """Print this help."""
        if cmd is None:
            coms = OrderedDict()
            com_list = [
                'help', 'info', 'uptime', 'poke', 'roll',
                'stream', 'join', 'leave', 'kick', 'ban']
            space = list_align(com_list, 2)
            for com in com_list:
                coms[com] = self.bot.commands[com]
            message = ['Available commands:', '```']
            for i, com in enumerate(coms):
                message.append('{}{}: {}'.format(
                    com, ' ' * space[i], coms[com].help.splitlines()[0]))
            message.append(
                '\nTo see help for individual commands, '
                'use {}help command'.format(self.bot.command_prefix))
            message.append('```')
            message = '\n'.join(message)
            await self.bot.say(message)
        else:
            try:
                message = self.bot.commands[cmd].help.format(
                    prefix=self.bot.command_prefix)
            except:
                return
            await self.bot.say('```' + message + '```')

    @commands.command()
    async def info(self):
        """Print bot information."""
        lib_link = 'https://github.com/Rapptz/discord.py/tree/async'
        source_link = 'https://github.com/mikevb1/discordbot'
        message = """This bot is written in Python using discord.py from {}.
    The source code can be found at {}.""".format(lib_link, source_link)
        await self.bot.say(message)

    @commands.command()
    async def uptime(self):
        """Display bot uptime."""
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            fmt = '{d} day{dp}, {h} hour{hp}, {m} minute{mp}, {s} second{sp}'
        elif hours:
            fmt = '{h} hour{hp}, {m} minute{mp}, {s} second{sp}'
        elif minutes:
            fmt = '{m} minute{mp}, {s} second{sp}'
        else:
            fmt = '{s} second{sp}'

        def plural(num):
            return 's' if num != 1 else ''

        up = fmt.format(
            d=days, dp=plural(days),
            h=hours, hp=plural(hours),
            m=minutes, mp=plural(minutes),
            s=seconds, sp=plural(seconds))
        await self.bot.say('Uptime: **{}**'.format(up))

    @commands.command()
    async def poke(self):
        """Make sure bot is working."""
        replies = [
            'Hey!', 'Ow!', 'Stop that!', "I'm here!", 'I need an adult!']
        await self.bot.say(random.choice(replies))

    @commands.command(name='id', pass_context=True)
    async def get_id(self, ctx):
        """Get discord ID's."""
        for m in ctx.message.mentions:
            await self.bot.say('{0.name}: {0.id}'.format(m))

    @commands.command()
    async def join(self, channel):
        """Tell bot to join server using ID or discord.gg link.

        Usage:
        {prefix}join 0h4QlpGEPGkSCO6I                    (invite ID)
        {prefix}join https://discord.gg/0h4QlpGEPGkSCO6I (invite link)
        """
        try:
            await self.bot.accept_invite(channel)
        except:
            pass

    @commands.command(pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def leave(self, ctx):
        """Tell bot to leave server."""
        await self.bot.leave_server(ctx.message.server)


def setup(bot):
    """'Magic' function to set up cog."""
    bot.add_cog(Meta(bot))
