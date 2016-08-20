from collections import OrderedDict
import datetime

from discord.ext import commands
import discord


class Meta:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def info(self):
        """Display bot information."""
        message = []
        if self.bot.source:
            message.append('The source code can be found at {0.source}.')
        message.append('The developer is {0.owner}.')
        message = '\n'.join(message).format(self.bot)
        await self.bot.say(message)

    @commands.command()
    async def uptime(self):
        """Display bot uptime."""
        now = datetime.datetime.utcnow()
        delta = now - self.bot.start_time
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

    @commands.command(pass_context=True, aliases=['ping'])
    async def poke(self, ctx):
        """Make sure bot is working."""
        if ctx.invoked_with == 'poke':
            reply = 'I need an adult!'
        else:
            reply = 'Pong!'
        await self.bot.say(reply)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Meta(bot))
