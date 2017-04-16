import datetime

from discord.ext import commands
import discord

from utils.utils import pluralize, integer
from cogs.base import BaseCog


class Management(BaseCog):
    """Admin/moderation commands."""
    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, *, member: discord.Member):
        """Kick user from server if you have permission.

        You must have permission to kick members.
        """
        try:
            await ctx.guild.kick(member)
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick.")
        except discord.HTTPException:
            await ctx.send('Kicking failed.')
        else:
            await ctx.send('\N{THUMBS UP SIGN}')

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, *, member: discord.Member):
        """Ban user from server.

        You must have permission to ban members.
        """
        try:
            await ctx.guild.ban(member)
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban.")
        except discord.HTTPException:
            await ctx.send('Banning failed.')
        else:
            await ctx.send('\N{THUMBS UP SIGN}')

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, count: integer, *, member: discord.Member=None):
        """Purge up to 100 messages from the current channel.

        [member] is optional and will default to everyone.
        You must have proper permissions to remove others' messages.
        Note this only goes back through the last 1000 messages or 14 days.
        """
        if count > 100:
            await ctx.send('Can only purge up to 100 messages.')
            return
        message = ctx.message
        author = message.author
        channel = message.channel
        earliest = message.created_at - datetime.timedelta(days=14)

        if member is None or member == author or \
                channel.permissions_for(author).manage_messages or \
                (member == ctx.guild.me and author.id == self.bot.owner.id):
            to_remove = []
            async for msg in channel.history(before=message, after=earliest, limit=1000):
                if member is None or msg.author == member:
                    to_remove.append(msg)
                if len(to_remove) == count:
                    break
            try:
                if len(to_remove) == 0:
                    pass
                elif len(to_remove) == 1:
                    await to_remove[0].delete()
                else:
                    await channel.delete_messages(to_remove)
            except discord.Forbidden:
                await ctx.send("{} message{} couldn't be deleted.".format(
                    *(('The', '') if len(to_remove) < 1 else ('Some', 's'))))
            except discord.HTTPException:
                await ctx.send("There was an error deleting the message{}.".format(
                    's' if len(to_remove) > 1 else ''))
            else:
                await ctx.send(pluralize(f'Removed {len(to_remove)} message{{}}.'))


def setup(bot):
    bot.add_cog(Management(bot))
