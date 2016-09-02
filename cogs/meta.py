from datetime import datetime

from discord.ext import commands
import discord
import aiohttp

from .utils import checks, utils


class Meta:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(hidden=True)
    async def manage(self):
        """Manage bot user attributes."""
        pass

    @manage.command(rest_is_raw=True)
    @checks.is_owner()
    async def name(self, *, new_name):
        """Rename bot."""
        if new_name:
            await self.bot.edit_profile(username=new_name)

    async def set_avatar_by_url(self, url):
        with aiohttp.Timeout(10):
            async with self.bot.aiohsession.get(url) as resp:
                if resp.status != 200:
                    return
                await self.bot.edit_profile(avatar=await resp.read())

    @manage.command(pass_context=True)
    @checks.is_owner()
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

    @manage.command(pass_context=True, rest_is_raw=True)
    @commands.bot_has_permissions(change_nickname=True)
    @checks.owner_or_permissions(manage_nicknames=True)
    async def nick(self, ctx, *, new_nick):
        """Change bot's nickname."""
        bot_member = ctx.message.server.me
        await self.bot.change_nickname(bot_member, new_nick or None)

    @commands.command()
    async def source(self):
        """Display bot information."""
        message = []
        message.append('My developer is {0.owner}.')
        if self.bot.source:
            message.append('My source code can be found at {0.source}.')
        message = '\n'.join(message).format(self.bot)
        await self.bot.say(message)

    def fancy_time(self, orig_time):
        diff = datetime.utcnow() - orig_time
        nice = ''
        if diff.days >= 365:
            nice += str(diff.days // 365) + ' years, '
        nice += str(diff.days % 365) + ' days ago'
        nice += ' ({} UTC)'.format(orig_time)
        return nice

    @commands.command(pass_context=True)
    async def info(self, ctx, *, member: discord.Member=None):
        """Display information on the bot or a specific user."""
        message = []
        member = member or ctx.message.server.me

        roles = [role.name.replace('@', '@\u200b')
                 for role in member.roles]
        roles.remove('@\u200beveryone')

        message.append('```xl')
        lines = [
            ('Name', member.name),
            ('Tag', member.discriminator),
            ('ID', member.id),
            ('Joined Server', self.fancy_time(member.joined_at)),
            ('Joined Discord', self.fancy_time(member.created_at)),
            ('Roles', ', '.join(roles)),
            ('Avatar', member.avatar_url)]
        width = max(len(k) for k, v in lines) + 1
        for line in lines:
            message.append('{0:<{width}}: {1}'.format(*line,
                                                      width=width))
        message.append('```')
        message = '\n'.join(message)
        await self.bot.say(message)

    @commands.command()
    async def uptime(self):
        """Display bot uptime."""
        now = datetime.utcnow()
        delta = now - self.bot.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if days:
            fmt = '{d} day{dp}, {h} hour{hp}, {m} minute{mp}, {s} second{sp}'
        elif hours:
            fmt = '{h} hour{hp}, {m} minute{mp}, {s} second{sp}'
        elif minutes:
            fmt = '{m} minute{mp}, {s} second{sp}'
        else:
            fmt = '{s} second{sp}'

        up = fmt.format(
            d=days, dp=utils.plural(days),
            h=hours, hp=utils.plural(hours),
            m=minutes, mp=utils.plural(minutes),
            s=seconds, sp=utils.plural(seconds))
        await self.bot.say('```xl\nUptime: {}\n```'.format(up))

    @commands.command(pass_context=True, aliases=['ping'])
    async def poke(self, ctx):
        """Make sure bot is working."""
        if ctx.invoked_with == 'poke':
            reply = 'I need an adult!'
        else:
            reply = 'Pong!'
        await self.bot.say(reply)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Meta(bot))
