from xml.etree import ElementTree as XMLTree
import datetime
import asyncio
import random

from discord.ext import commands
import discord
import aiohttp

from utils.checks import bot_config_attr, need_db
from utils.errors import NotFound
from utils.utils import between, integer
from utils.emoji import digits
from cogs.base import BaseCog


FACTS = 'http://catfacts-api.appspot.com/api/facts?number={count}'

HOME = 'http://thecatapi.com/'
HOME_BY_ID = HOME + '?id={image_id}'
GET = HOME + 'api/images/get?api_key={api_key}&format=xml{category}&sub_id={sub_id}'
REPORT = HOME + 'api/images/report?api_key={api_key}&sub_id={sub_id}&image_id={image_id}{reason}'
VOTE = HOME + 'api/images/vote?api_key={api_key}&sub_id={sub_id}&image_id={image_id}&score={score}'
GET_VOTES = HOME + 'api/images/getvotes?api_key={api_key}&sub_id={sub_id}'
FAVE = HOME + 'api/images/favourite?api_key={api_key}&sub_id={sub_id}&image_id={image_id}&action={act}'
GET_FAVES = HOME + 'api/images/getfavourites?api_key={api_key}&sub_id={sub_id}'

CATEGORIES = {'hats', 'space', 'funny', 'sunglasses', 'boxes',
              'caturday', 'ties', 'dream', 'sinks', 'clothes'}


def xkcd_date(data):
    if 'date' in data:  # data is an asyncpg record
        date = data['date']
    else:  # data is a dict from xkcd api
        date = datetime.date(*map(int, (data['year'], data['month'], data['day'])))
    return date


class MostRecent(Exception):
    pass


class Reported(Exception):
    pass


class Images(BaseCog):
    """Commands to fetch images from various sources."""
    def make_xkcd_url(self, num='', api=True):
        url = 'http://xkcd.com/'
        if num:
            url += str(num) + '/'
        if api:
            url += 'info.0.json'
        return url

    async def fetch_xkcd(self, num=''):
        url = self.make_xkcd_url(num)
        status, data = await self.bot.request(url)
        if status != 200:
            raise NotFound('Could not get comic.')
        else:
            return data

    async def xkcd_insert(self, ctx, data):
        async with ctx.con.transaction():
            return await ctx.con.execute('''
                INSERT INTO xkcd VALUES ($1, $2, $3, $4, $5)
                ''', data['num'], data['safe_title'],
                data['alt'], data['img'], xkcd_date(data))

    @need_db
    @commands.command()
    async def xkcd(self, ctx, comic=''):
        """Get xkcd comics.

        [comic] can be the number of a comic or "r"/"rand"/"random"
        """
        data = None
        with ctx.typing():
            try:
                if comic in {'r', 'rand', 'random'} or not comic:
                    data = await self.fetch_xkcd()
                    await ctx.con.fetchrow('''
                        SELECT * FROM xkcd WHERE num = $1
                        ''', data['num']) or await self.xkcd_insert(ctx, data)
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
                data = await ctx.con.fetchrow('''
                    SELECT * FROM xkcd WHERE num = $1
                    ''', comic) or await self.fetch_xkcd(comic)
                if isinstance(data, dict):
                    await self.xkcd_insert(ctx, data)
            except NotFound as e:
                await ctx.send(e)
                return
            except MostRecent:
                pass

            description = f'**Date:** {xkcd_date(data):%m/%d/%Y}\n{data["alt"]}'
            # embed = discord.Embed(title='{0[num]}: {0[safe_title]}'.format(data),
            embed = discord.Embed(title=f'{data["num"]}: {data["safe_title"]}',
                                  url=self.make_xkcd_url(data['num'], api=False),
                                  description=description)
            embed.set_image(url=data['img'])
        await ctx.send(embed=embed)

    async def fetch_facts(self, count):
        status, j = await self.bot.request(FACTS.format(count=count))
        if status != 200 or (j is not None and j['success'] != 'true'):
            raise NotFound('No cat fact available.')
        return j['facts']

    async def fetch_cat(self, url, **format_args):
        url = url.format(api_key=self.bot.config['cat_api'],
                         reason=format_args.pop('reason', ''),
                         **format_args)
        status, data = await self.bot.request(url, 'text')
        if status != 200:
            raise NotFound('Could not get cat.')
        return data

    async def try_cat_image(self, url, attempt=1):
        if url is None:
            return False
        try:
            resp = await self.bot.request(url, 'read')
        except aiohttp.ClientOSError:  # DNS name not resolved
            return False
        else:
            return resp.status == 200

    @commands.group(invoke_without_command=True)
    @bot_config_attr('cat_api')
    async def cat(self, ctx, category=''):
        """Get a random cat image.

        [category] can be one of:
            hats, space, funny, sunglasses,
            boxes, caturday, ties, dream,
            sinks, clothes

        Within 30 seconds of the image being posted anyone can react with :poop: to report the image.
        Please only report images that do not contain cats.
        """
        if category in CATEGORIES:
            category = '&category=' + category
        elif category:
            await ctx.send('Invalid category. Try one of: ' + ', '.join(CATEGORIES))
        sub_id = ctx.author.id
        with ctx.typing():
            try:
                while True:
                    try:
                        x = await self.fetch_cat(GET, category=category, sub_id=sub_id)
                    except aiohttp.ClientResponseError:
                        continue
                    image_root = XMLTree.fromstring(x).find('data').find('images').find('image')
                    image_url = image_root.find('url').text
                    image_id = image_root.find('id').text
                    if await self.try_cat_image(image_url):
                        break
                    else:
                        await self.fetch_cat(REPORT, sub_id=sub_id,
                                             image_id=image_id,
                                             reason='DNS name not resolved')
            except NotFound as e:
                await ctx.send(str(e))
                return

            try:
                fact = (await self.fetch_facts(1))[0]
            except NotFound as e:
                fact = ''

            embed = discord.Embed(title=image_id, url=HOME_BY_ID.format(image_id=image_id),
                                  description=fact or None, color=discord.Color.red())
            embed.set_image(url=image_url)
            embed.set_footer(text='React with \N{PILE OF POO} to report this image.')
            msg = await ctx.send(embed=embed)

        def report_check(reaction, user):
            return reaction.message.id == msg.id and reaction.emoji == '\N{PILE OF POO}'

        try:
            await self.bot.wait_for('reaction_add', check=report_check, timeout=30)
        except asyncio.TimeoutError:
            pass
        else:
            await self.fetch_cat(REPORT, sub_id=sub_id, image_id=image_id)
            return
        finally:
            embed.set_footer()
            embed.color = discord.Color.default()
            await msg.edit(embed=embed)

    @cat.command(name='facts', aliases=['fact'])
    async def cat_facts(self, ctx, count: integer = 1):
        """Get cat facts.

        1 <= [count] <= 20
        """
        count = between(count, 1, 20)
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
                msg.add_line(f'{ind + 1}. {fact}')
            for page in msg.pages:
                await ctx.send(page)
        else:
            await ctx.send(facts[0])

    @cat_facts.error
    async def cat_facts_error(self, exc, ctx):
        if isinstance(exc, commands.BadArgument):
            pass
        else:
            ctx.command = ctx.command.name
            await self.bot.on_command_error(exc, ctx)


def setup(bot):
    bot.add_cog(Images(bot))
