"""Cog for miscellaneous stuff."""

from discord.ext import commands
import asyncio


class Misc:
    """Miscellaneous functions/commands and stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot


def setup(bot):
    """'Magic' function to set up cog."""
    bot.add_cog(Misc(bot))
