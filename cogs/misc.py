from collections import OrderedDict
import random

from discord.ext import commands
import aiohttp


class Misc:
    def __init__(self, bot):
        self.bot = bot
        self.aiohsession = aiohttp.ClientSession(loop=bot.loop)

    @commands.command(rest_is_raw=True)
    async def roll(self, *, args):
        """In format XdY, rolls X dice each with Y sides.

        If X is neglected, it will be assumed to mean 1 die.
        You can also specify a list of dice to roll. "1d6 2d20 d12"
        """
        args = args.split() or ['1d6']
        dice = []
        try:
            for arg in args:
                die = arg.split('d')
                die[0] = die[0] or 1
                dice.append(tuple(map(int, die)))
        except:
            return

        sides = 0
        rolls = []
        for tup in dice:
            count = tup[0]
            if len(tup) != 1:
                sides = tup[1]
            for i in range(1, count + 1):
                rolls.append(str(random.randint(1, sides or 6)))

        message = ', '.join(rolls)
        await self.bot.say(message)

    @commands.command()
    async def flip(self, coins: int=1):
        """Flip any number of coins."""
        flips = OrderedDict([('Heads', 0),
                             ('Tails', 0),
                             ('Edge', 0)])

        for _ in range(coins):
            rand = random.randint(0, 6000)
            if rand:
                if rand % 2:
                    flips['Heads'] += 1
                else:
                    flips['Tails'] += 1
            else:  # 1/6001 chance of being edge
                flips['Edge'] += 1

        message = []
        for f, c in flips.items():
            if c:
                if coins == 1:
                    message.append(f)
                    break
                message.append('{}: {}'.format(f, c))
        message = '\n'.join(message)
        await self.bot.say(message)

    def make_xkcd_url(self, num=''):
        url = 'http://xkcd.com/'
        if num:
            url += str(num) + '/'
        url += 'info.0.json'
        return url

    async def fetch_xkcd(self, url):
        with aiohttp.Timeout(10):
            async with self.aiohsession.get(url) as resp:
                return resp.status, await resp.json()

    @commands.command()
    async def xkcd(self, comic=''):
        """Get xkcd comics.

        [comic] can be the number of a comic or "r"/"rand"/"random"
        """
        latest_url = self.make_xkcd_url()

        if comic in ('r', 'rand', 'random'):
            status, data = await self.fetch_xkcd(latest_url)
            if status != 200:
                await self.bot.say('Could not get comic.')
                return
            latest = data['num']
            comic = str(random.randint(1, latest))

        url = self.make_xkcd_url(comic) if comic.isdigit() else latest_url

        status, data = await self.fetch_xkcd(url)
        if status != 200:
            await self.bot.say('Could not get comic.')
            return

        message = '**Title**: {0[safe_title]}' \
                  '\n**Alt Text**: {0[alt]}' \
                  '\n**Image**: {0[img]}'.format(data)
        await self.bot.say(message)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
