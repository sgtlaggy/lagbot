"""Cog for administration stuff."""

from discord.ext import commands
import asyncio


class Admin:
    """Server admin stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot

    @commands.command()
    async def join(self, channel):
        """Tell bot to join server using ID or discord.gg link.

        Usage:
        {0}join 0h4QlpGEPGkSCO6I                    (invite ID)
        {0}join https://discord.gg/0h4QlpGEPGkSCO6I (invite link)
        """
        try:
            await self.bot.accept_invite(channel)
        except:
            pass

    @commands.command(pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def leave(self, ctx):
        """Tell bot to leave server.

        Usage:
        {0}leave
        """
        await self.bot.leave_server(ctx.message.server)

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
