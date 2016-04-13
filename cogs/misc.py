"""Cog for miscellaneous stuff."""

from discord.ext import commands
import asyncio
import random


class Misc:
    """Miscellaneous functions/commands and stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot

    @commands.command()
    async def roll(self, dice='1d6'):
        """In format XdY, rolls X dice each with Y sides. Default: 1d6"""
        try:
            count, sides = map(int, dice.split('d'))
        except:
            return
        message = []
        for i in range(1, count + 1):
            value = random.randint(1, sides)
            message.append('Roll{}: {}'.format(
                ' ' + i if count > 1 else '',
                value))
        message = '\n'.join(message)
        await self.bot.say(message)


def setup(bot):
    """'Magic' function to set up cog."""
    bot.add_cog(Misc(bot))
