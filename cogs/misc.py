from xml.etree import ElementTree as XMLTree
from collections import OrderedDict
import datetime
import asyncio
import random
import re

from discord.ext import commands
import aiohttp

from .utils.checks import bot_config_attr
from .utils.utils import NotFound


GET = 'http://thecatapi.com/api/images/get?api_key={api_key}&format=xml{category}&sub_id={sub_id}'
VOTE = 'http://thecatapi.com/api/images/vote?api_key={api_key}&sub_id={sub_id}&image_id={image_id}&score={score}'
CATEGORIES = ('hats', 'space', 'funny', 'sunglasses', 'boxes',
              'caturday', 'ties', 'dream', 'sinks', 'clothes')


class MostRecent(Exception):
    pass


class Misc:
    def __init__(self, bot):
        self.bot = bot

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

    async def fetch_xkcd(self, num=''):
        url = self.make_xkcd_url(num)
        with aiohttp.Timeout(10):
            async with self.bot.aiohsession.get(url) as resp:
                if resp.status != 200:
                    raise NotFound('Could not get comic.')
                return await resp.json()

    def xkcd_date(self, data):
        if 'date' in data:
            date = data['date']
        else:
            date = datetime.date(*map(int, (data['year'],
                                            data['month'],
                                            data['day'])))
        return date

    async def xkcd_insert(self, data):
        async with self.bot.db.transaction():
            return await self.bot.db.execute('''
                INSERT INTO xkcd VALUES ($1, $2, $3, $4, $5)
                ''', data['num'], data['safe_title'],
                data['alt'], data['img'], self.xkcd_date(data))

    @commands.command()
    async def xkcd(self, comic=''):
        """Get xkcd comics.

        [comic] can be the number of a comic or "r"/"rand"/"random"
        """
        data = None
        try:
            if comic in ('r', 'rand', 'random') or not comic:
                data = await self.fetch_xkcd()
                await self.bot.db.fetchrow('''
                    SELECT * FROM xkcd WHERE num = $1
                    ''', data['num']) or await self.xkcd_insert(data)
                if not comic:
                    raise MostRecent
                while True:
                    comic = random.randint(1, data['num'])
                    if comic != 404:
                        break
            else:
                if not comic.isdigit():
                    return
                comic = int(comic)
            data = await self.bot.db.fetchrow('''
                SELECT * FROM xkcd WHERE num = $1
                ''', comic) or await self.fetch_xkcd(comic)
            if isinstance(data, dict):
                await self.xkcd_insert(data)
        except NotFound as e:
            await self.bot.say(e)
            return
        except MostRecent:
            pass

        message = '**Date**: {1:%m/%d/%Y}' \
                  '\n**Title**: {0[num]}. {0[safe_title]}' \
                  '\n**Alt Text**: {0[alt]}' \
                  '\n**Image**: {0[img]}'.format(data, self.xkcd_date(data))
        await self.bot.say(message)

    async def fetch_cat(self, url):
        with aiohttp.Timeout(10):
            async with self.bot.aiohsession.get(url) as resp:
                if resp.status != 200:
                    raise NotFound('Could not get cat.')
                return await resp.text()

    @commands.command(pass_context=True)
    @bot_config_attr('cat_api')
    async def cat(self, ctx, category=''):
        """Get a random cat image.

        [category] can be one of:
            hats, space, funny, sunglasses,
            boxes, caturday, ties, dream,
            sinks, clothes

        Up to 20 users can rate images by sending a message within 15 seconds in the format "X/10"
        """
        if category and category in CATEGORIES:
            category = '&category=' + category
        else:
            category = ''
        sub_id = ctx.message.author.id
        try:
            x = await self.fetch_cat(GET.format(api_key=self.bot.config['cat_api'],
                                                category=category, sub_id=sub_id))
        except NotFound as e:
            await self.bot.say(str(e))
            return

        image_root = XMLTree.fromstring(x)[0][0][0]  # [response][data][images][image]
        image_url = image_root[0].text
        image_id = image_root[1].text
        image_msg = await self.bot.say(
            '{image}\nReply with X/10 to rate this image.'.format(image=image_url))

        votes = []
        voted = []

        def vote_check(msg):
            if msg.channel != ctx.message.channel or msg.author.id in voted:
                return False
            match = re.match(r'-?[0-9]*/10', msg.content)
            if match is None:
                return False
            sub_id = msg.author.id
            voted.append(sub_id)
            score = int(msg.content.split('/')[0])
            if score > 10:
                score = 10
            elif score < 1:
                score = 1
            votes.append(self.fetch_cat(VOTE.format(api_key=self.bot.config['cat_api'],
                                                    sub_id=sub_id, score=score,
                                                    image_id=image_id)))

        await self.bot.wait_for_message(timeout=15, check=vote_check)
        await self.bot.edit_message(image_msg, image_url)
        await asyncio.gather(*votes)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
