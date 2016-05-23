from collections import OrderedDict
import datetime
import random

from discord.ext import commands
import discord
import asyncio

from .utils import checks


class Meta:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help')
    async def help_cmd(self, cmd=None):
        """Print this help."""
        if cmd is None:
            coms = OrderedDict()
            com_list = [
                'help', 'info', 'uptime', 'poke', 'roll',
                'stream', 'join', 'leave', 'kick', 'ban']
            width = max(map(lambda t: len(t), com_list)) + 1
            for com in com_list:
                coms[com] = self.bot.commands[com]
            message = ['Available commands:', '```']
            for i, com in enumerate(coms):
                message.append('{0:<{width}}: {1}'.format(
                    com, coms[com].help.splitlines()[0], width=width))
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
        source_link = 'https://github.com/mikevb1/discordbot'
        message = 'The source code can be found at {}.'.format(source_link)
        if self.bot.owner_name:
            message += '\nThe developer is {}.'.format(self.bot.owner_name)
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
        elif seconds:
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

    @commands.command()
    async def join(self):
        """Add bot to one of your servers."""
        if self.bot.client_id is None:
            return
        perm = discord.Permissions()
        perm.kick_members = True
        perm.ban_members = True
        perm.read_messages = True
        perm.send_messages = True
        perm.manage_messages = True
        perm.embed_links = True
        url = discord.utils.oauth_url(self.bot.client_id, permissions=perm)
        await self.bot.say(url)

    @commands.command(pass_context=True)
    @checks.owner_or_permissions(kick_members=True)
    async def leave(self, ctx):
        """Tell bot to leave server."""
        await self.bot.leave_server(ctx.message.server)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Meta(bot))
