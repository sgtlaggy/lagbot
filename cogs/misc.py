import random

from discord.ext import commands
import aiohttp


class Misc:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, dice='1d6'):
        """In format XdY, rolls X dice each with Y sides. Default: 1d6

        Usage:
        {prefix}roll
        {prefix}roll XdY
        """
        try:
            count, sides = map(int, dice.split('d'))
        except:
            return
        message = []
        for i in range(1, count + 1):
            value = random.randint(1, sides)
            message.append('Roll{}: {}'.format(
                ' ' + str(i) if count > 1 else '',
                value))
        message = '\n'.join(message)
        await self.bot.say(message)

    @commands.command()
    async def xkcd(self, comic=''):
        """Get xkcd comics.

        Usage:
        {prefix}xkcd
        {prefix}xkcd 327
        """
        url = 'http://xkcd.com/'
        if comic.isdigit():
            url += comic + '/'
        url += 'info.0.json'
        async with aiohttp.get(url) as resp:
            if resp.status != 200:
                await self.bot.say('Could not get comic.')
                return
            data = await resp.json()
        # this seemed to be the nicest-looking way to write this
        # without stupid indentation on multi-line string
        message = '\n'.join(['**Title**: {0[safe_title]}',
                             '**Alt Text**: {0[alt]}',
                             '**Image**: {0[img]}']).format(data)
        await self.bot.say(message)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
