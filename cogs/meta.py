from discord.ext import commands
import discord

from utils.utils import db_encode, db_decode
from utils.checks import need_db
from cogs.base import BaseCog
from utils import checks


class Meta(BaseCog):
    """Commands that are related to the bot itself."""
    @commands.group(pass_context=False, hidden=True)
    async def manage(self):
        """Manage bot user attributes."""
        pass

    @need_db
    @manage.group(invoke_without_command=True)
    @checks.owner_or_permissions(manage_guild=True)
    async def prefix(self, ctx, new_prefix: str, allow_default=False):
        """Set a custom prefix for this guild.

        Manage Server permission is required to use this.
        [allow_default] should be enabled if you want to also
                        be able to use the default prefix
        """
        guild = ctx.guild
        if len(new_prefix) > 25:
            await ctx.send('That prefix is too long, please choose a new one.')
            return
        async with ctx.con.transaction():
            await ctx.con.execute('''
                INSERT INTO prefixes (guild_id, prefix, allow_default) VALUES ($1, $2, $3)
                ON CONFLICT (guild_id)
                DO UPDATE SET (prefix, allow_default) = ($2, $3)
                ''', guild.id, db_encode(new_prefix), allow_default)
        await ctx.send(f'Set custom prefix to "{new_prefix}".')

    @need_db
    @prefix.command()
    @checks.owner_or_permissions(manage_guild=True)
    async def reset(self, ctx):
        """Remove this guild's custom prefix."""
        guild = ctx.guild
        async with ctx.con.transaction():
            res = await ctx.con.execute('''
                DELETE FROM prefixes WHERE guild_id = $1
                ''', guild.id)
        if res[-1] == '0':
            await ctx.send("A custom prefix hasn't been set for this guild.")
        else:
            await ctx.send('Removed custom prefix for this guild.')

    @need_db
    @prefix.command()
    async def show(self, ctx):
        """Show the prefix set for this guild.

        Also shows whether or not the default prefix can be used.
        """
        rec = await ctx.con.fetchrow('''
            SELECT * FROM prefixes WHERE guild_id = $1
            ''', str(ctx.guild.id))
        if rec is None:
            await ctx.send("A custom prefix hasn't been set for this guild.")
            return

        prefix, allow_default = rec['prefix'], rec['allow_default']
        valid = [db_decode(prefix)]
        default = self.bot.default_prefix
        if allow_default:
            if isinstance(default, (tuple, list)):
                valid.extend(default)
            else:
                valid.append(default)

        embed = discord.Embed()
        embed.add_field(name='Custom Prefix', value=valid[0])
        embed.add_field(name='Allow Default', value=str(rec['allow_default']))
        embed.add_field(name='Valid Prefixes', value='\n'.join(valid))
        await ctx.send(embed=embed)

    @manage.command(pass_context=False)
    @commands.is_owner()
    async def name(self, *, new_name=None):
        """Rename bot."""
        if new_name:
            await self.bot.edit_profile(username=new_name)

    @manage.command(aliases=['game'])
    @commands.is_owner()
    async def status(self, ctx, *, new_status=None):
        """Change bot's online status or game name."""
        bot_member = self.bot.guilds[0].me
        if ctx.invoked_with == 'game':
            await self.bot.change_presence(
                game=discord.Game(name=new_status),
                status=bot_member.status)
        else:
            await self.bot.change_presence(
                game=bot_member.game,
                status=getattr(discord.Status, new_status or '', 'online'))

    async def set_avatar_by_url(self, url):
        status, image = await self.bot.request(url, 'read')
        if status != 200:
            return
        await self.bot.edit_profile(avatar=image)

    @manage.command()
    @commands.is_owner()
    async def avatar(self, ctx, new_avatar=None):
        """Change bot's avatar.

        new_avatar can be a link to an image,
        left blank with an attached image,
        or left blank with no attachment to remove image
        """
        if new_avatar is not None:
            await self.set_avatar_by_url(new_avatar)
        else:
            if len(ctx.message.attachments):
                await self.set_avatar_by_url(ctx.message.attachments[0]['url'])
            else:
                await self.bot.edit_profile(avatar=None)

    @manage.command()
    @commands.guild_only()
    @commands.bot_has_permissions(change_nickname=True)
    @checks.owner_or_permissions(manage_nicknames=True)
    async def nick(self, ctx, *, new_nick=None):
        """Change bot's nickname."""
        await ctx.guild.me.edit(nick=new_nick or None)

    @commands.command(aliases=['restart', 'kill'], hidden=True)
    @commands.is_owner()
    async def exit(self, ctx, code: int = None):
        """Restart/kill the bot.

        Optionally set exit code for custom handling.
        """
        codes = {'restart': 2, 'kill': 1}
        code = codes.get(ctx.invoked_with, code)
        if code is None:
            await ctx.send('Invalid exit code.')
            return
        self.bot.exit_status = code
        await self.bot.logout()

    @property
    def oauth_url(self):
        perms = discord.Permissions()
        perms.update(kick_members=True,
                     ban_members=True,
                     read_messages=True,
                     read_message_history=True,
                     send_messages=True,
                     manage_messages=True,
                     embed_links=True,
                     change_nickname=True,
                     add_reactions=True)
        return discord.utils.oauth_url(self.bot.app.id, permissions=perms)

    @commands.command()
    async def join(self, ctx):
        """Add bot to one of your servers.

        Bots can no longer accept instant invite links.
        You can only invite/add bots to servers you create.
        This command gives you a link to add this bot to your servers.
        """
        desc = '\n'.join([
            'Follow this link, login if necessary, then select a server you own to add me to.',
            'The requested permissions are required for some of my commands to function.'])
        embed = discord.Embed(title='Click here!',
                              url=self.oauth_url,
                              description=desc)
        await ctx.send(embed=embed)

    @commands.command()
    async def about(self, ctx):
        """Display bot information."""
        description = 'Uptime: {}\n[Invite Link]({})'.format(self.bot.get_uptime(brief=True),
                                                             self.oauth_url)
        embed = discord.Embed(description=description)
        embed.set_author(name=str(self.bot.app.owner),
                         icon_url=self.bot.app.owner.avatar_url)
        if callable(self.bot.command_prefix):
            valid_prefix = await self.bot.command_prefix(self.bot, ctx.message)
        else:
            valid_prefix = self.bot.command_prefix
        if isinstance(valid_prefix, list):
            docs = 'Say ' + ' or '.join(f'{prefix}help' for prefix in valid_prefix)
        else:
            docs = f'Say {valid_prefix}help'
        if self.bot.config.get('userdocs'):
            docs += ' or see [here]({0.config[userdocs]})'
        docs += '.'
        embed.add_field(name='Documentation', value=docs.format(self.bot))
        source = self.bot.config.get('source')
        if source:
            embed.add_field(name='Source', value=f'See [here]({source}).')
        embed.set_footer(text='Made with discord.py | Online Since', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = self.bot.start_time
        await ctx.send(embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """Display bot uptime."""
        uptime = '\n'.join(self.bot.get_uptime().split(', '))
        embed = discord.Embed(
            description=f'```ocaml\nUptime:\n{uptime}\n```',
            timestamp=self.bot.start_time)
        embed.set_footer(text='Online Since')
        await ctx.send(embed=embed)

    @commands.command(aliases=['ping'])
    async def poke(self, ctx):
        """Make sure bot is working."""
        if ctx.invoked_with == 'poke':
            reply = 'I need an adult!'
        else:
            reply = 'Pong!'
        await ctx.send(reply)


def setup(bot):
    bot.add_cog(Meta(bot))
