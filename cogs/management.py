import datetime

from discord.ext import commands
import discord

from utils.utils import pluralize, integer
from utils.checks import need_db
from cogs.base import BaseCog


def date(argument):
    formats = ('%Y/%m/%d', '%Y-%m-%d')
    for fmt in formats:
        try:
            return datetime.strptime(argument, fmt)
        except ValueError:
            continue
    raise commands.BadArgument('Cannot convert to date. Expected YYYY/MM/DD or YYYY-MM-DD.')


class Management(BaseCog):
    """Admin/moderation commands."""
    @need_db
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def newrole(self, ctx, role: discord.Role = None):
        """Automatically give new members a role.

        Call without a role to see current role.
        You can pass role as case-sensitive role name or role ID to avoid mentions.
        """
        if role is None:
            role_id = await ctx.con.fetchval('''
                SELECT role_id FROM newrole WHERE guild_id = $1
                ''', ctx.guild.id)
            if role_id is None:
                return await ctx.send('A role has not been set for this guild.')
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            if role is None:
                async with ctx.con.transaction():
                    await ctx.con.execute('''
                        DELETE FROM newrole WHERE guild_id = $1
                        ''', ctx.guild.id)
                await ctx.send('A role has not been set for this guild.')
            else:
                await ctx.send(f'"{role.name}" is the current role for new members.')
        else:
            async with ctx.con.transaction():
                await ctx.con.execute('''
                    INSERT INTO newrole (guild_id, role_id) VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO
                    UPDATE SET role_id = $2 WHERE newrole.guild_id = $1
                    ''', ctx.guild.id, role.id)
            await ctx.send(f'The role "{role.name}" will be given to new members.')

    @need_db
    @newrole.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def off(self, ctx):
        """Stop automically giving new members a role."""
        async with ctx.con.transaction():
            await ctx.con.execute('''
                DELETE FROM newrole WHERE guild_id = $1
                ''', ctx.guild.id)
        await ctx.send('Disabled automatic role assignment.')

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, count: integer, member: discord.Member=None, *, reason=None):
        """Purge up to 100 messages from the current channel.

        [member] is optional and will default to everyone.
        You must have proper permissions to remove others' messages.
        Note this only goes back through the last 1000 messages or 14 days.
        """
        if count > 100:
            return await ctx.send('Can only purge up to 100 messages.')
        if reason is None:
            reason = f'request by {ctx.message.author}'
        else:
            reason = f'{reason} -{ctx.message.author}'
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
                    await to_remove[0].delete(reason=reason)
                else:
                    await channel.delete_messages(to_remove, reason=reason)
            except discord.Forbidden:
                await ctx.send("{} message{} couldn't be deleted.".format(
                    *(('The', '') if len(to_remove) < 1 else ('Some', 's'))))
            except discord.HTTPException:
                await ctx.send("There was an error deleting the message{}.".format(
                    's' if len(to_remove) > 1 else ''))
            else:
                await ctx.send(pluralize(f'Removed {len(to_remove)} message{{}}.'))

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def nostalgia(self, ctx, date: date = None, *, channel: discord.TextChannel = None):
        """Pins an old message from a specific date.

        If a date is not given, then pins first message from the channel.
        If a channel is not given, then pins from the channel the
        command was ran on.

        The format of the date must be either YYYY-MM-DD or YYYY/MM/DD.
        """

        if channel is None:
            channel = ctx.channel
        if date is None:
            date = channel.created_at

        async for m in ctx.history(after=date, limit=1):
            try:
                await m.pin()
            except:
                await ctx.send('\N{THUMBS DOWN SIGN} Could not pin message.')

    @nostalgia.error
    async def nostalgia_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

    async def on_member_join(self, member):
        """Automatically assign roles if guild has a role set through `newrole` command."""
        if not member.guild.me.guild_permissions.manage_roles:
            return
        async with self.bot.db_pool.acquire() as con:
            role_id = await con.fetchval('''
                SELECT role_id FROM newrole WHERE guild_id = $1
                ''', member.guild.id)
            if role_id is None:
                return
            role = discord.utils.get(member.guild.roles, id=role_id)
            if role is None:
                async with con.transaction():
                    return await con.execute('''
                        DELETE FROM newrole WHERE guild_id = $1
                        ''', member.guild.id)
        await member.add_roles(role, reason='New Member')


def setup(bot):
    bot.add_cog(Management(bot))
