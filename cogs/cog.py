import asyncio
import logging

from discord.ext import commands

from .utils import checks
from .base import BaseCog


class CogManagement(BaseCog):
    """Cog management commands, owner only."""
    async def reload_ext_helper(self, ext):
        try:
            self.bot.unload_extension('cogs.{}'.format(ext))
            self.bot.load_extension('cogs.{}'.format(ext))
        except:
            await ctx.send("Couldn't reload cog {}.".format(ext))

    @commands.command(name='cogs', hidden=True)
    @checks.is_owner()
    async def list_exts(self, ctx):
        exts = sorted(self.bot.extensions.keys())
        message = '\n'.join(['```', 'Loaded extensions:', *exts, '```'])
        await ctx.send(message)

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    @checks.is_owner()
    async def reload_ext(self, ctx, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod not in self.bot.extensions:
                await ctx.send('Cog {} is not loaded.'.format(ext))
                return
            try:
                await self.reload_ext_helper(ext)
                await ctx.send('Reloaded cog {}.'.format(ext))
            except Exception as e:
                await ctx.send("Couldn't reload cog {}.".format(ext))
                logging.error("Couldn't reload cog {}.".format(ext))

    @reload_ext.command(name='all')
    @checks.is_owner()
    async def reload_all_exts(self, ctx):
        exts = [e.split('.')[1] for e in self.bot.extensions.keys()]
        await asyncio.gather(*[self.reload_ext_helper(ext) for ext in exts])
        await ctx.send('Reloaded all cogs.')

    @commands.command(name='load', hidden=True)
    @checks.is_owner()
    async def load_ext(self, ctx, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod in self.bot.extensions:
                await ctx.send('Cog {} is already loaded.'.format(ext))
                return
            try:
                self.bot.load_extension(mod)
                await ctx.send('Loaded cog {}.'.format(ext))
            except Exception as e:
                await ctx.send("Couldn't load cog {}.".format(ext))
                logging.error("Couldn't load cog {}.".format(ext))

    @commands.command(name='unload', hidden=True)
    @checks.is_owner()
    async def unload_ext(self, ctx, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod not in self.bot.extensions:
                await ctx.send('Cog {} is not loaded.'.format(ext))
                return
            try:
                self.bot.unload_extension(mod)
                await ctx.send('Unloaded cog {}.'.format(ext))
            except Exception as e:
                await ctx.send("Couldn't unload cog {}.".format(ext))
                logging.error("Couldn't unload cog {}.".format(ext))


def setup(bot):
    bot.add_cog(CogManagement(bot))
