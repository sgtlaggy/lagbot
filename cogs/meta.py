from discord.ext import commands
import discord

import config


class Meta(commands.Cog):
    """Commands that are related to the bot itself."""
    def __init__(self, bot):
        self.bot = bot

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

    @commands.group(hidden=True)
    @commands.is_owner()
    async def manage(self, ctx):
        """Manage bot user attributes."""
        pass

    @manage.command()
    @commands.is_owner()
    async def name(self, ctx, *, new_name):
        """Rename bot."""
        await self.bot.user.edit(username=new_name)

    async def set_avatar_by_url(self, url):
        status, image = await self.bot.request(url, 'read')
        if status != 200:
            return
        await self.bot.user.edit(avatar=image)

    @manage.command()
    @commands.is_owner()
    async def avatar(self, ctx, new_avatar=None):
        """Change bot's avatar.

        Accepted values:
        image link
        omitted, attach image
        omitted, no attachment (reset avatar to default)
        """
        if new_avatar is not None:
            await self.set_avatar_by_url(new_avatar)
        else:
            if ctx.message.attachments:
                new_avatar = await ctx.message.attachments[0].read()
            await self.bot.user.edit(avatar=new_avatar)

    @property
    def oauth_url(self):
        perms = discord.Permissions()
        perms.update(manage_messages=True,
                     read_messages=True,
                     send_messages=True,
                     embed_links=True)
        return discord.utils.oauth_url(self.bot.app.id, permissions=perms)

    @commands.command()
    async def invite(self, ctx):
        """Add bot to one of your servers."""
        desc = '\n'.join([
            'Follow this link, login if necessary, then select a server you moderate to add me to.',
            'The requested permissions are required for some of my commands to function.'])
        embed = discord.Embed(title='Click here!', url=self.oauth_url, description=desc)
        await ctx.send(embed=embed)

    @commands.command()
    async def about(self, ctx):
        """Display bot information."""
        description = f'Uptime: {self.bot.get_uptime(brief=True)}'
        embed = discord.Embed(title='Invite me to your server!', url=self.oauth_url, description=description)
        app = self.bot.app
        if app.team:
            embed.add_field(name='Team', value='\n'.join(str(m) for m in app.team.members))
        else:
            embed.set_author(name=str(app.owner), icon_url=app.owner.display_avatar)
        embed.add_field(name='Guilds', value=str(len(self.bot.guilds)))
        source = config.source
        if source:
            embed.add_field(name='Source', value=f'See [here]({source}).')
        embed.set_footer(text='Made with discord.py | Online Since', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = self.bot.start_time
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """Make sure bot is working."""
        await ctx.send(f'Pong! Latency: {int(self.bot.latency * 1000)}ms')


def setup(bot):
    bot.add_cog(Meta(bot))
