from discord.ext import commands
import discord

from .utils.utils import plural, integer
from .base import BaseCog


class Management(BaseCog):
    """Admin/moderation commands."""
    @commands.command(no_pm=True)
    @commands.has_permissions(kick_members=True)
    async def kick(self, *, member: discord.Member):
        """Kick user from server if you have permission.

        You must have permission to kick members.
        """
        try:
            await self.bot.kick(member)
        except discord.Forbidden:
            await self.bot.say("I don't have permission to kick.")
        except discord.HTTPException:
            await self.bot.say('Kicking failed.')
        else:
            await self.bot.say('\N{THUMBS UP SIGN}')

    @commands.command(no_pm=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, *, member: discord.Member):
        """Ban user from server.

        You must have permission to ban members.
        """
        try:
            await self.bot.ban(member)
        except discord.Forbidden:
            await self.bot.say("I don't have permission to ban.")
        except discord.HTTPException:
            await self.bot.say('Banning failed.')
        else:
            await self.bot.say('\N{THUMBS UP SIGN}')

    @commands.command(pass_context=True, no_pm=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, count: integer, *, member: discord.Member=None):
        """Purge messages from the current channel.

        You must have proper permissions to remove others' messages.
        Note this only goes back through the last 1000 messages.
        """
        message = ctx.message
        author = message.author
        channel = message.channel
        owner = ctx.message.server.get_member(self.bot.owner.id)
        if member is None:
            member = author

        if member == author or \
                channel.permissions_for(author).manage_messages or \
                (member == ctx.message.server.me and author == owner):
            to_remove = []
            async for msg in self.bot.logs_from(channel, before=message, limit=1000):
                if msg.author == member:
                    to_remove.append(msg)
                if len(to_remove) == count:
                    break
            if len(to_remove) == 0:
                await self.bot.say("{} hasn't sent any messages.".format(member))
                return
            elif len(to_remove) == 1:
                await self.bot.delete_message(to_remove[0])
            else:
                await self.bot.delete_messages(to_remove)
            await self.bot.say('Removed {} message{} by {}.'.format(
                len(to_remove), plural(len(to_remove)), member.display_name),
                delete_after=10)


def setup(bot):
    bot.add_cog(Management(bot))
