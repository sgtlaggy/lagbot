"""Cog for administration stuff."""

from discord.ext import commands
import asyncio


class Admin:
    """Server admin stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot

    @commands.command(pass_context=True)
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx):
        """Kick user from server if you have permission.

        Usage:
        {0}kick @user
        """
        for m in ctx.message.mentions:
            await self.bot.kick(m)

    @commands.command(pass_context=True)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, _, days=1):
        """Ban user from server if you have permission.

        Usage:
        {0}ban @user
        """
        days = int(days)
        if days > 7:
            days = 7
        elif days < 0:
            days = 0
        await self.bot.ban(ctx.message.mentions[0], days)


def setup(bot):
    """'Magic' function to set up cog."""
    bot.add_cog(Admin(bot))
