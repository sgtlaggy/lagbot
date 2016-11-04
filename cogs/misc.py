from xml.etree import ElementTree as XMLTree
from collections import OrderedDict
import datetime
import asyncio
import random
import re

from discord.ext import commands
import aiohttp

from .utils.utils import between, integer
from .utils.checks import bot_config_attr
from .utils.errors import NotFound


class CatAction:
    def __init__(self, action, uid, score=None):
        self.action = action
        self.id = uid
        self.score = score


FACTS = 'http://catfacts-api.appspot.com/api/facts?number={count}'

GET = 'http://thecatapi.com/api/images/get?api_key={api_key}&format=xml{category}&sub_id={sub_id}'
REPORT = 'http://thecatapi.com/api/images/report?api_key={api_key}&sub_id={sub_id}&image_id={image_id}&reason={reason}'
VOTE = 'http://thecatapi.com/api/images/vote?api_key={api_key}&sub_id={sub_id}&image_id={image_id}&score={score}'
GET_VOTES = 'http://thecatapi.com/api/images/getvotes?api_key={api_key}&sub_id={sub_id}'
FAVE = 'http://thecatapi.com/api/images/favourite?api_key={api_key}&sub_id={sub_id}&image_id={image_id}&action={act}'
GET_FAVES = 'http://thecatapi.com/api/images/getfavourites?api_key={api_key}&sub_id={sub_id}'
CATEGORIES = ('hats', 'space', 'funny', 'sunglasses', 'boxes',
              'caturday', 'ties', 'dream', 'sinks', 'clothes')

REACTIONS = ['\N{PILE OF POO}',
             '\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT SEVEN}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT EIGHT}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{DIGIT NINE}\N{COMBINING ENCLOSING KEYCAP}',
             '\N{KEYCAP TEN}',
             '\N{HEAVY BLACK HEART}']


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
    async def flip(self, coins: integer = 1):
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

    async def fetch_xkcd(self, num='', attempt=1):
        try:
            url = self.make_xkcd_url(num)
            with aiohttp.Timeout(10):
                async with self.bot.aiohsession.get(url) as resp:
                    if resp.status != 200:
                        raise NotFound('Could not get comic.')
                    return await resp.json()
        except aiohttp.ClientResponseError:
            if attempt == 3:
                raise NotFound('Could not get comic.')
            await asyncio.sleep(1)
            return await self.fetch_xkcd(num, attempt + 1)

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
        await self.bot.type()
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

    async def fetch_facts(self, count, attempt=1):
        try:
            with aiohttp.Timeout(10):
                async with self.bot.aiohsession.get(FACTS.format(count=count)) as resp:
                    j = await resp.json()
                    if resp.status != 200 or j['success'] != 'true':
                        raise NotFound('No cat fact available.')
                    return j['facts']
        except aiohttp.ClientResponseError:
            if attempt == 3:
                raise NotFound('No cat fact available.')
            else:
                await asyncio.sleep(1)
                return await self.fetch_facts(count, attempt + 1)

    async def fetch_cat(self, url, attempt=1, **format_args):
        try:
            url = url.format(api_key=self.bot.config['cat_api'], **format_args)
            with aiohttp.Timeout(10):
                async with self.bot.aiohsession.get(url) as resp:
                    if resp.status != 200:
                        raise NotFound('Could not get cat.')
                    return await resp.text()
        except aiohttp.ClientResponseError:
            if attempt == 3:
                raise NotFound('Could not get cat.')
            else:
                await asyncio.sleep(1)
                return await self.fetch_cat(url, attempt + 1, **format_args)

    @commands.group(pass_context=True, invoke_without_command=True)
    @bot_config_attr('cat_api')
    async def cat(self, ctx, category=''):
        """Get a random cat image.

        [category] can be one of:
            hats, space, funny, sunglasses,
            boxes, caturday, ties, dream,
            sinks, clothes

        Within 30 seconds of the image being posted anyone can react with:
            * 1-10 to rate the image.
            * heart to favorite the image.
            * poop to report the image.
        """
        if category and category in CATEGORIES:
            category = '&category=' + category
        else:
            category = ''
        sub_id = ctx.message.author.id
        try:
            await self.bot.type()
            x = await self.fetch_cat(GET, category=category, sub_id=sub_id)
        except NotFound as e:
            await self.bot.say(str(e))
            return
        try:
            fact = (await self.fetch_facts(1))[0]
        except NotFound as e:
            fact = ''

        image_root = XMLTree.fromstring(x).find('data').find('images').find('image')
        image_url = image_root.find('url').text
        image_id = image_root.find('id').text
        base_msg = '`{id}`: {url}\n{fact}'.format(id=image_id, url=image_url,
                                                  fact=fact)
        image_msg = await self.bot.say('\n'.join([
            base_msg,
            'For the next 30 seconds you can select:',
            '- :one:-:keycap_ten: to rate this image',
            '- :heart: to favorite this image',
            '- :poop: to report this image']).format(REACTIONS))
        for reaction in REACTIONS[1:]:
            await self.bot.add_reaction(image_msg, reaction)

        actions = []
        votes = {}
        faved = set()
        reported = False

        def vote_check(reaction, user):
            sub_id = user.id
            score = REACTIONS.index(reaction.emoji)
            if 1 <= score <= 10:
                votes[sub_id] = score
            elif score == 11:
                faved.add(sub_id)
                actions.append(self.fetch_cat(FAVE, sub_id=sub_id,
                                              image_id=image_id,
                                              act='add'))
            else:
                if reported:
                    return False
                nonlocal reported
                reported = True
                actions.append(self.fetch_cat(REPORT, sub_id=sub_id,
                                              image_id=image_id))
            if len(actions) + len(votes) == 20:
                return True

        await self.bot.wait_for_reaction(REACTIONS, timeout=30,
                                         message=image_msg, check=vote_check)
        await self.bot.edit_message(image_msg, base_msg)
        for reaction in REACTIONS[1:]:
            await self.bot.remove_reaction(image_msg, reaction, self.bot.user)

        for sub_id, score in votes.items():
            actions.append(self.fetch_cat(VOTE, sub_id=sub_id,
                                          image_id=image_id,
                                          score=score))
        await asyncio.gather(*actions)

    @cat.command(name='facts', aliases=['fact'])
    async def cat_facts(self, count: float = 1):
        """Get cat facts.

        0 < [count] <= 20
        """
        if count < 0:
            count = 1
        else:
            count = between(count, 0, 20)
        partial = count - int(count)
        count = int(count)
        if partial:
            count += 1
        elif count == 0:
            return

        try:
            facts = await self.fetch_facts(count)
        except NotFound as e:
            facts = [str(e)]
        else:
            if partial:
                end_ind = int(len(facts[-1]) * partial)
                facts[-1] = facts[-1][:end_ind] or facts[-1][0]

        if len(facts) > 1:
            msg = commands.Paginator(prefix='', suffix='')
            for ind, fact in enumerate(facts):
                msg.add_line('{}. {}'.format(ind + 1, fact))
            for page in msg.pages:
                await self.bot.say(page)
        else:
            await self.bot.say(facts[0])

    @cat_facts.error
    async def cat_facts_error(self, exc, ctx):
        if isinstance(exc, commands.BadArgument):
            pass
        else:
            ctx.command = ctx.command.name
            await self.bot.on_command_error(exc, ctx)

    @cat.command(pass_context=True)
    async def ratings(self, ctx):
        """Get a list of images you've rated.

        To change your rating of an image, see the "rerate" command.
        """
        sub_id = ctx.message.author.id
        await self.bot.type()
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
        await self.bot.type()
        root = XMLTree.fromstring(await self.fetch_cat(GET_VOTES, sub_id=sub_id))
        ids = [i.text for i in root.iter('id')]
        if image_id not in ids:
            await self.bot.say('Invalid image_id.')
            return
        if new_score.isdigit():
            score = between(int(new_score), 1, 10)
        elif new_score in REACTIONS[1:11]:
            score = REACTIONS.index(new_score)
        else:
            score_match = re.match(r'(-?[0-9]*)/10', new_score)
            if score_match is None:
                await self.bot.say('Invalid score format.')
                return
            score = between(int(score_match.group(1)), 1, 10)
        await self.fetch_cat(VOTE, sub_id=sub_id, image_id=image_id, score=score)
        await self.bot.say('\N{THUMBS UP SIGN} Changed your rating.')

    @cat.command(pass_context=True, aliases=['faves', 'favourites'])
    async def favorites(self, ctx, to_remove=None):
        """Get a list of your favorited images.

        Images are posted in format "ID: url".
        [to_remove] is an ID of the image you want to unfavorite.
        """
        sub_id = ctx.message.author.id
        await self.bot.type()
        root = XMLTree.fromstring(await self.fetch_cat(GET_FAVES, sub_id=sub_id))
        ids = [i.text for i in root.iter('id')]
        urls = [u.text for u in root.iter('url')]

        if to_remove is not None:
            if to_remove not in ids:
                await self.bot.say("That's not in your favorites.")
                return
            await self.fetch_cat(FAVE, sub_id=sub_id,
                                 image_id=to_remove,
                                 act='remove')
            await self.bot.say('\N{THUMBS UP SIGN} Removed favorite.')
            return

        msg = ['`{id}`: {url}'.format(id=i, url=u) for i, u in zip(ids, urls)]
        if len(msg):
            await self.bot.say('\n'.join(msg))
        else:
            await self.bot.say('You have no favorites!')


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
