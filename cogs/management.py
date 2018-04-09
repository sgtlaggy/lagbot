import datetime

from discord.ext import commands
import discord

from utils.utils import pluralize, integer
from utils.checks import need_db
from cogs.base import BaseCog
import config


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

    def __init__(self, bot):
        super().__init__(bot)
        self.tts = {}

    @need_db
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def newrole(self, ctx, *, role: discord.Role = None):
        """Automatically give new members a role.

        Call without a role to see current role.
        You can pass role as case-sensitive role name or role ID to avoid mentions.
        My bot integration role must be higher than the new user role.
        """
        if role is None:
            role_id = await ctx.con.fetchval('''
                SELECT role_id FROM newrole WHERE guild_id = $1
                ''', ctx.guild.id)
            if role_id is None:
                await ctx.send('A role has not been set for this guild.')
                return
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
        bot_role = discord.utils.get(ctx.me.roles, managed=True)
        if role is not None and role.position > bot_role.position:
            await ctx.send(f'Please move "{role}" above "{bot_role}" in the role list.')

    @need_db
    @newrole.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def autoadd(self, ctx, toggle: bool = None):
        """Check or set whether to automatically add the new role.

        If enabled, the new role will automatically be added if a user has all other roles removed.
        """
        state = await ctx.con.fetchval('''
            SELECT autoadd FROM newrole WHERE guild_id = $1
            ''', ctx.guild.id)
        if state is None:
            await ctx.send('New role is not set for this guild.')
        elif toggle is None:
            await ctx.send(f'New role autoadd is set to {"enabled" if state else "disabled"}')
        else:
            async with ctx.con.transaction():
                await ctx.con.execute('''
                    UPDATE newrole SET autoadd = $1 WHERE guild_id = $2
                    ''', toggle, ctx.guild.id)
            await ctx.send(f'New role adding is now {"enabled" if toggle else "disabled"}')

    @need_db
    @newrole.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def autoremove(self, ctx, toggle: bool = None):
        """Check or set whether to automatically remove the new role.

        If enabled, the new role will automatically be removed when the user is assigned another role.
        """
        state = await ctx.con.fetchval('''
            SELECT autoremove FROM newrole WHERE guild_id = $1
            ''', ctx.guild.id)
        if state is None:
            await ctx.send('New role is not set for this guild.')
        elif toggle is None:
            await ctx.send(f'New role autoremoval is set to {"enabled" if state else "disabled"}')
        else:
            async with ctx.con.transaction():
                await ctx.con.execute('''
                    UPDATE newrole SET autoremove = $1 WHERE guild_id = $2
                    ''', toggle, ctx.guild.id)
            await ctx.send(f'New role removal is now {"enabled" if toggle else "disabled"}')

    @need_db
    @newrole.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def off(self, ctx):
        """Stop automically giving new members a role."""
        exists = await ctx.con.fetchval('''
            SELECT EXISTS(SELECT 1 FROM newrole WHERE guild_id = $1)
            ''', ctx.guild.id)
        if not exists:
            await ctx.send('New role is not set for this guild.')
            return
        async with ctx.con.transaction():
            await ctx.con.execute('''
                DELETE FROM newrole WHERE guild_id = $1
                ''', ctx.guild.id)
        await ctx.send('Disabled automatic role assignment.')

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
            async for msg in channel.history(before=message, after=earliest, limit=1000, reverse=False):
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

    @commands.command(aliases=['join', 'add'])
    @commands.guild_only()
    async def addrole(self, ctx: commands.Context, *, name):
        """Add yourself to a role/group.

        To make a role available to these commands, it should have no permissions granted.
        """
        name = name.lower()
        for r in ctx.guild.roles:
            if r.name.lower() == name and r.permissions == discord.Permissions.none():
                role = r
                break
            elif r.name.lower() == name:
                await ctx.send('That role is not available for use with this command.')
                return
        else:
            await ctx.send('That role does not exist.')
            return
        await ctx.author.add_roles(role)
        await ctx.send(f'Added role "{role}".')

    @commands.command(aliases=['leave', 'remove'])
    @commands.guild_only()
    async def removerole(self, ctx, *, name):
        """Remove yourself from a role/group.

        To make a role available to these commands, it should have no permissions granted.
        """
        name = name.lower()
        for r in ctx.author.roles:
            if r.name.lower() == name and r.permissions == discord.Permissions.none():
                role = r
                break
            elif r.name.lower() == name:
                await ctx.send('That role is not available for use with this command.')
                return
        else:
            await ctx.send('You do not have that role.')
            return
        await ctx.author.remove_roles(role)
        await ctx.send(f'Removed role "{role}".')

    @commands.command()
    async def autotts(self, ctx, toggle: bool = None):
        """Automatically makes every message sent to this channel TTS."""
        if toggle is None:
            status = 'enabled' if self.tts.get(ctx.channel.id) else 'disabled'
            await ctx.send(f'AutoTTS is {status} for this channel.')
            return
        self.tts[ctx.channel.id] = toggle
        status = 'enabled' if toggle else 'disabled'
        await ctx.send(f'AutoTTS is now {status} for this channel.')

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

    async def on_message(self, message):
        view = commands.view.StringView(message.content)
        if self.tts.get(message.channel.id) and message.author.id != self.bot.user.id and \
                not any(view.skip_string(p) for p in await bot.command_prefix(bot, msg)) and not message.tts:
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(f'{message.author.name} says {message.content}', tts=True)

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
                    await con.execute('''
                        DELETE FROM newrole WHERE guild_id = $1
                        ''', member.guild.id)
                return
        await member.add_roles(role, reason='New Member')

    async def on_member_update(self, before, after):
        """Remove new role when user is assigned another role."""
        len_before = len(before.roles)
        len_after = len(after.roles)
        guild = after.guild
        if not guild.me.guild_permissions.manage_roles or len_before == len_after:
            return
        async with self.bot.db_pool.acquire() as con:
            settings = await con.fetchrow('''
                SELECT * FROM newrole WHERE guild_id = $1
                ''', guild.id)
            if settings is None or not (settings['autoremove'] or settings['autoadd']):
                return
            newrole = discord.utils.get(guild.roles, id=settings['role_id'])
            if newrole is None:
                async with con.transaction():
                    await con.execute('''
                        DELETE FROM newrole WHERE guild_id = $1
                        ''', member.guild.id)
                return
        if newrole.position > guild.me.top_role.position:
            return
        if settings['autoremove'] and len_after > len_before:
            if newrole not in after.roles:
                return
            await after.remove_roles(newrole, reason=f'{config.prefix}newrole autoremove')
        elif settings['autoadd'] and len_after == 1:  # all roles removed, only has @everyone
            await after.add_roles(newrole, reason=f'{config.prefix}newrole autoadd')


def setup(bot):
    bot.add_cog(Management(bot))
