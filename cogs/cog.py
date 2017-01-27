import asyncio
import logging

from discord.ext import commands

from cogs.base import BaseCog
from utils import checks


class CogManagement(BaseCog):
    """Cog management commands, owner only."""
    async def reload_ext_helper(self, ctx, ext):
        try:
            self.bot.unload_extension(f'cogs.{ext}')
            self.bot.load_extension(f'cogs.{ext}')
        except:
            await ctx.send(f"Couldn't reload cog {ext}.")

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
                await ctx.send(f'Cog {ext} is not loaded.')
                return
            try:
                await self.reload_ext_helper(ctx, ext)
                await ctx.send(f'Reloaded cog {ext}.')
            except Exception as e:
                await ctx.send(f"Couldn't reload cog {ext}.")
                logging.error(f"Couldn't reload cog {ext}.")

    @reload_ext.command(name='all')
    @checks.is_owner()
    async def reload_all_exts(self, ctx):
        exts = [e.split('.')[1] for e in self.bot.extensions.keys()]
        await asyncio.gather(*[self.reload_ext_helper(ctx, ext) for ext in exts])
        await ctx.send('Reloaded all cogs.')

    @commands.command(name='load', hidden=True)
    @checks.is_owner()
    async def load_ext(self, ctx, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod in self.bot.extensions:
                await ctx.send(f'Cog {ext} is already loaded.')
                return
            try:
                self.bot.load_extension(mod)
                await ctx.send(f'Loaded cog {ext}.')
            except Exception as e:
                await ctx.send(f"Couldn't load cog {ext}.")
                logging.error(f"Couldn't load cog {ext}.")

    @commands.command(name='unload', hidden=True)
    @checks.is_owner()
    async def unload_ext(self, ctx, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod not in self.bot.extensions:
                await ctx.send(f'Cog {ext} is not loaded.')
                return
            try:
                self.bot.unload_extension(mod)
                await ctx.send(f'Unloaded cog {ext}.')
            except Exception as e:
                await ctx.send(f"Couldn't unload cog {ext}.")
                logging.error(f"Couldn't unload cog {ext}.")


def setup(bot):
    bot.add_cog(CogManagement(bot))
