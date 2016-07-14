from collections import OrderedDict
import datetime
import random

from discord.ext import commands
import discord


class Meta:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def info(self):
        """Display bot information."""
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


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Meta(bot))
