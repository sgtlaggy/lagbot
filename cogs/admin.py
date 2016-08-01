from discord.ext import commands
import discord

from .utils import checks


class Management:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
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
            await self.bot.say('\U0001f44c')

    @commands.command()
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
            await self.bot.say('\U0001f44c')

    @commands.command()
    async def join(self):
        """Add bot to one of your servers.

        Bots can no longer accept instant invite links.
        You can only invite/add bots to servers you create.
        This command gives you a link to add this bot to your servers.
        """
        perm = discord.Permissions()
        perm.kick_members = True
        perm.ban_members = True
        perm.read_messages = True
        perm.send_messages = True
        perm.manage_messages = True
        perm.embed_links = True
        url = discord.utils.oauth_url(self.bot.client_id, permissions=perm)
        message = []
        message.append('Follow this link, login if necessary, then select a '
                       'server you own to add me to.')
        message.append('The requested permissions are required for some of '
                       'my commands to function.')
        message.append(url)
        await self.bot.say('\n'.join(message))

    @commands.command(pass_context=True)
    @checks.owner_or_permissions(kick_members=True)
    async def leave(self, ctx):
        """Tell bot to leave server.

        You must have permission to kick members.
        """
        await self.bot.leave_server(ctx.message.server)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Management(bot))
