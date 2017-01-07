from discord.ext import commands
import discord

from .utils.utils import plural, integer
from .base import BaseCog


class Management(BaseCog):
    """Admin/moderation commands."""
    @commands.command(no_pm=True)
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, *, member: discord.Member):
        """Kick user from server if you have permission.

        You must have permission to kick members.
        """
        try:
            await ctx.message.guild.kick(member)
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick.")
        except discord.HTTPException:
            await ctx.send('Kicking failed.')
        else:
            await ctx.send('\N{THUMBS UP SIGN}')

    @commands.command(no_pm=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, *, member: discord.Member):
        """Ban user from server.

        You must have permission to ban members.
        """
        try:
            await ctx.message.guild.ban(member)
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban.")
        except discord.HTTPException:
            await ctx.send('Banning failed.')
        else:
            await ctx.send('\N{THUMBS UP SIGN}')

    @commands.command(no_pm=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, count: integer, *, member: discord.Member=None):
        """Purge messages from the current channel.

        You must have proper permissions to remove others' messages.
        Note this only goes back through the last 1000 messages.
        """
        message = ctx.message
        author = message.author
        channel = message.channel
        owner = ctx.message.guild.get_member(self.bot.owner.id)
        if member is None:
            member = author

        if member == author or \
                channel.permissions_for(author).manage_messages or \
                (member == ctx.message.guild.me and author == owner):
            to_remove = []
            async for msg in channel.history(before=message, limit=1000):
                if msg.author == member:
                    to_remove.append(msg)
                if len(to_remove) == count:
                    break
            if len(to_remove) == 0:
                await ctx.send(f"{member.display_name} hasn't sent any messages.")
                return
            elif len(to_remove) == 1:
                await to_remove[0].delete()
            else:
                await ctx.delete_messages(to_remove)
            await ctx.send('Removed {} message{} by {}.'.format(
                len(to_remove), plural(len(to_remove)), member.display_name),
                delete_after=10)


def setup(bot):
    bot.add_cog(Management(bot))
