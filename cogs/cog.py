import asyncio

from discord.ext import commands

from .utils import checks
from .base import BaseCog


class CogManagement(BaseCog):
    async def reload_ext_helper(self, ext):
        try:
            self.bot.unload_extension('cogs.{}'.format(ext))
            self.bot.load_extension('cogs.{}'.format(ext))
        except:
            await self.bot.say("Couldn't reload cog {}.".format(ext))

    @commands.command(name='cogs', hidden=True)
    @checks.is_owner()
    async def list_exts(self):
        exts = sorted(self.bot.extensions.keys())
        message = '\n'.join(['```', 'Loaded extensions:', *exts, '```'])
        await self.bot.say(message)

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    @checks.is_owner()
    async def reload_ext(self, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod not in self.bot.extensions:
                await self.bot.say('Cog {} is not loaded.'.format(ext))
                return
            try:
                await self.reload_ext_helper(ext)
                await self.bot.say('Reloaded cog {}.'.format(ext))
            except Exception as e:
                await self.bot.say("Couldn't reload cog {}.".format(ext))
                print(e)

    @reload_ext.command(name='all')
    @checks.is_owner()
    async def reload_all_exts(self):
        exts = [e.split('.')[1] for e in self.bot.extensions.keys()]
        await asyncio.gather(*[self.reload_ext_helper(ext) for ext in exts])
        await self.bot.say('Reloaded all cogs.')

    @commands.command(name='load', hidden=True)
    @checks.is_owner()
    async def load_ext(self, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod in self.bot.extensions:
                await self.bot.say('Cog {} is already loaded.'.format(ext))
                return
            try:
                self.bot.load_extension(mod)
                await self.bot.say('Loaded cog {}.'.format(ext))
            except Exception as e:
                await self.bot.say("Couldn't load cog {}.".format(ext))
                print(e)

    @commands.command(name='unload', hidden=True)
    @checks.is_owner()
    async def unload_ext(self, *exts):
        for ext in exts:
            mod = 'cogs.' + ext
            if mod not in self.bot.extensions:
                await self.bot.say('Cog {} is not loaded.'.format(ext))
                return
            try:
                self.bot.unload_extension(mod)
                await self.bot.say('Unloaded cog {}.'.format(ext))
            except Exception as e:
                await self.bot.say("Couldn't unload cog {}.".format(ext))
                print(e)


def setup(bot):
    bot.add_cog(CogManagement(bot))
