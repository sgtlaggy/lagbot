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
GET_VOTES = 'http://thecatapi.com/api/images/getvotes?api_key={api_key}&sub_id={sub_id}'
FAV = 'http://thecatapi.com/api/images/favourite?api_key={api_key}&sub_id={sub_id}&image_id={image_id}&action={act}'
GET_FAVS = 'http://thecatapi.com/api/images/getfavourites?api_key={api_key}&sub_id={sub_id}'
CATEGORIES = ('hats', 'space', 'funny', 'sunglasses', 'boxes',
              'caturday', 'ties', 'dream', 'sinks', 'clothes')


def cat_score(score: int):
    if score > 10:
        return 10
    elif score < 1:
        return 1
    return score


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

    async def fetch_cat(self, url, **format_args):
        url = url.format(api_key=self.bot.config['cat_api'], **format_args)
        with aiohttp.Timeout(10):
            async with self.bot.aiohsession.get(url) as resp:
                if resp.status != 200:
                    raise NotFound('Could not get cat.')
                return await resp.text()

    @commands.group(pass_context=True, invoke_without_command=True)
    @bot_config_attr('cat_api')
    async def cat(self, ctx, category=''):
        """Get a random cat image.

        [category] can be one of:
            hats, space, funny, sunglasses,
            boxes, caturday, ties, dream,
            sinks, clothes

        Within 15 seconds of the image being posted anyone can:
            * Say "X/10" (1-10) to rate the image.
            * Say "fav"/"favorite"/"favourite" to favorite the image.
        """
        if category and category in CATEGORIES:
            category = '&category=' + category
        else:
            category = ''
        sub_id = ctx.message.author.id
        try:
            x = await self.fetch_cat(GET, category=category, sub_id=sub_id)
        except NotFound as e:
            await self.bot.say(str(e))
            return

        image_root = XMLTree.fromstring(x)
        image_url = image_root.find('url').text
        image_id = image_root.find('id').text
        image_msg = await self.bot.say(
            '{id}: {url}\nReply with "X/10" to rate this image or "fave" to favorite it.'.format(id=image_id, url=image_url))

        actions = []
        voted = []
        faved = []

        def vote_check(msg):
            if msg.channel != ctx.message.channel:
                return False
            sub_id = msg.author.id
            score_match = re.match(r'(-?[0-9]*)/10', msg.content)
            if score_match is not None:
                if sub_id in voted:
                    return False
                voted.append(sub_id)
                score = cat_score(int(score_match.group(1)))
                actions.append(self.fetch_cat(VOTE, sub_id=sub_id,
                                              image_id=image_id,
                                              score=score))
            else:
                if sub_id in faved:
                    return False
                fav_match = any(msg.content == f for f in ('fave', 'favorite', 'favourite'))
                if not fav_match:
                    return False
                faved.append(sub_id)
                actions.append(self.fetch_cat(FAV, sub_id=sub_id,
                                              image_id=image_id,
                                              act='add'))
            if len(actions) == 20:
                return True

        await self.bot.wait_for_message(timeout=15, check=vote_check)
        await self.bot.edit_message(image_msg, '{id}: {url}'.format(id=image_id, url=image_url))
        await asyncio.gather(*actions)

    @cat.command(pass_context=True)
    async def ratings(self, ctx):
        """Get a list of images you've rated.

        To change your rating of an image, see the "rerate" command.
        """
        sub_id = ctx.message.author.id
        root = XMLTree.fromstring(await self.fetch_cat(GET_VOTES, sub_id=sub_id))
        ids = [i.text for i in root.iter('id')]
        scores = [s.text for s in root.iter('score')]
        urls = [u.text for u in root.iter('url')]
        msg = ['```']
        msg.extend(['{score}/10 {id}: {url}'.format(score=s, id=i, url=u)
                    for s, i, u in zip(scores, ids, urls)])
        msg.append('```')
        if len(msg):
            await self.bot.say('\n'.join(msg))
        else:
            await self.bot.say("You haven't rated any images.")

    @cat.command(pass_context=True)
    async def rerate(self, ctx, image_id, new_score):
        """Re-rate an image you've rated before.

        <new_score> can be either just a number or "X/10"
        """
        sub_id = ctx.message.author.id
        root = XMLTree.fromstring(await self.fetch_cat(GET_VOTES, sub_id=sub_id))
        ids = [i.text for i in root.iter('id')]
        if image_id not in ids:
            await self.bot.say('Invalid image_id.')
            return
        if new_score.isdigit():
            score = cat_score(int(new_score))
        else:
            score_match = re.match(r'(-?[0-9]*)/10', new_score)
            if score_match is None:
                await self.bot.say('Invalid score format.')
                return
            score = cat_score(int(score_match.group(1)))
        await self.fetch_cat(VOTE, sub_id=sub_id, image_id=image_id, score=score)
        await self.bot.say('\N{THUMBS UP SIGN} Changed your rating.')

    @cat.command(pass_context=True, aliases=['faves', 'favourites'])
    async def favorites(self, ctx, to_remove=None):
        """Get a list of your favorited images.

        Images are posted in format "ID: url".
        [to_remove] is an ID of the image you want to unfavorite.
        """
        sub_id = ctx.message.author.id
        root = XMLTree.fromstring(await self.fetch_cat(GET_FAVS, sub_id=sub_id))
        ids = [i.text for i in root.iter('id')]
        urls = [u.text for u in root.iter('url')]

        if to_remove is not None:
            if to_remove not in ids:
                await self.bot.say("That's not in your favorites.")
                return
            await self.fetch_cat(FAV, sub_id=sub_id,
                                 image_id=to_remove,
                                 act='remove')
            await self.bot.say('\N{THUMBS UP SIGN} Removed favorite.')
            return

        msg = ['{id}: {url}'.format(id=i, url=u) for i, u in zip(ids, urls)]
        if len(msg):
            await self.bot.say('\n'.join(msg))
        else:
            await self.bot.say('You have no favorites!')


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
