import random

from discord.ext import commands
import aiohttp


class Misc:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, dice='1d6'):
        """In format XdY, rolls X dice each with Y sides."""
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
    async def flip(self, count=1):
        flips = []
        possible_flips = (['Heads'] * 500) + (['Tails'] * 500) + ['edge']
        for _ in range(count):
            flips.append(random.choice(possible_flips))
        message = []
        if count > 1:
            for f in set(possible_flips):
                if f in flips:
                    message.append('{}: {}'.format(f, flips.count(f)))
        else:
            message = flips
        message = '\n'.join(message)
        await self.bot.say(message)

    def make_xkcd_url(self, num=''):
        url = 'http://xkcd.com/'
        if num:
            url += str(num) + '/'
        url += 'info.0.json'
        return url

    async def fetch_xkcd(self, session, url):
        with aiohttp.Timeout(10):
            async with session.get(url) as resp:
                return resp.status, await resp.json()

    @commands.command()
    async def xkcd(self, comic=''):
        """Get xkcd comics.

        [comic] can be the number of a comic or one of 'r', 'rand', 'random'
        """
        latest_url = self.make_xkcd_url()

        with aiohttp.ClientSession(loop=self.bot.loop) as session:
            if comic in ('r', 'rand', 'random'):
                status, data = await self.fetch_xkcd(session, latest_url)
                if status != 200:
                    await self.bot.say('Could not get comic.')
                    return
                latest = data['num']
                comic = str(random.randint(1, latest))

            url = self.make_xkcd_url(comic) if comic.isdigit() else latest_url

            status, data = await self.fetch_xkcd(session, url)
            if status != 200:
                await self.bot.say('Could not get comic.')
                return

        # this seemed to be the nicest-looking way to write this
        # without stupid indentation on multi-line string
        message = '\n'.join(['**Title**: {0[safe_title]}',
                             '**Alt Text**: {0[alt]}',
                             '**Image**: {0[img]}']).format(data)
        await self.bot.say(message)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
