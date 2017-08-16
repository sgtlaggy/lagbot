import asyncio
import logging

from discord.ext import commands

from cogs.base import BaseCog
from utils import checks


class CogManagement(BaseCog):
    """Cog management commands, owner only."""
    async def reload_ext_helper(self, ctx, ext):
        self.bot.unload_extension(f'cogs.{ext}')
        self.bot.load_extension(f'cogs.{ext}')

    @commands.command(name='cogs', hidden=True)
    @commands.is_owner()
    async def list_exts(self, ctx):
        """List loaded extensions."""
        exts = sorted(self.bot.extensions.keys())
        message = '\n'.join(['```', 'Loaded extensions:', *exts, '```'])
        await ctx.send(message)

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    @commands.is_owner()
    async def reload_ext(self, ctx, *exts):
        """Reload specified extensions."""
        for ext in exts:
            mod = 'cogs.' + ext
            if mod not in self.bot.extensions:
                await ctx.send(f'Cog {ext} is not loaded.')
                continue
            try:
                await self.reload_ext_helper(ctx, ext)
                await ctx.send(f'Reloaded cog {ext}.')
            except Exception as e:
                await ctx.send(f"Couldn't reload cog {ext}.\n{e}")
                logging.exception(f"Couldn't reload cog {ext}.")

    @reload_ext.command(name='all')
    @commands.is_owner()
    async def reload_all_exts(self, ctx):
        """Reload all loaded extensions."""
        exts = [e.split('.')[1] for e in self.bot.extensions.keys()]
        await ctx.invoke(self.reload_ext, *exts)

    @commands.command(name='load', hidden=True)
    @commands.is_owner()
    async def load_ext(self, ctx, *exts):
        """Load specified extensions."""
        for ext in exts:
            mod = 'cogs.' + ext
            if mod in self.bot.extensions:
                await ctx.send(f'Cog {ext} is already loaded.')
                continue
            try:
                self.bot.load_extension(mod)
                await ctx.send(f'Loaded cog {ext}.')
            except Exception as e:
                await ctx.send(f"Couldn't load cog {ext}.\n{e}")
                logging.exception(f"Couldn't load cog {ext}.")

    @commands.command(name='unload', hidden=True)
    @commands.is_owner()
    async def unload_ext(self, ctx, *exts):
        """Unload specified extensions."""
        for ext in exts:
            mod = 'cogs.' + ext
            if mod not in self.bot.extensions:
                await ctx.send(f'Cog {ext} is not loaded.')
                continue
            try:
                self.bot.unload_extension(mod)
                await ctx.send(f'Unloaded cog {ext}.')
            except Exception as e:
                await ctx.send(f"Couldn't unload cog {ext}.\n{e}")
                logging.exception(f"Couldn't unload cog {ext}.")


def setup(bot):
    bot.add_cog(CogManagement(bot))
