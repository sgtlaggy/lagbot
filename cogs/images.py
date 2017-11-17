import datetime

from discord.ext import commands
import discord
import asyncpg

from utils.checks import need_db
from utils.errors import NotFound
from utils.utils import between, integer
from cogs.base import BaseCog


FACTS = 'https://catfact.ninja/facts?limit={count}'


def make_xkcd_url(num='', api=True):
    url = 'http://xkcd.com/'
    if num:
        url += str(num) + '/'
    if api:
        url += 'info.0.json'
    return url


def xkcd_date(data):
    if 'date' in data:  # data is an asyncpg record
        date = data['date']
    else:  # data is a dict from xkcd api
        date = datetime.date(*map(int, (data['year'], data['month'], data['day'])))
    return date


class Images(BaseCog):
    """Commands to fetch images from various sources."""
    async def fetch_xkcd(self, ctx, num=''):
        if num:
            if num in {'r', 'rand', 'random'}:
                url = 'https://c.xkcd.com/random/comic/'
                try:
                    async with self.bot.http_.get(url, timeout=10) as resp:
                        num = resp.url.split('/')[-2]
                except TimeoutError:
                    raise NotFound('Could not get comic.')
            try:
                rec = await ctx.con.fetchrow('''
                    SELECT * FROM xkcd WHERE num = $1
                    ''', int(num))
            except TypeError:
                raise NotFound('Could not get comic.')
            if rec:
                return rec
        else:
            rec = await ctx.con.fetchrow('''
                SELECT * FROM xkcd WHERE date = 'today'
                ''')
            if rec:
                return rec
        url = make_xkcd_url(num)
        try:
            status, data = await self.bot.request(url)
        except asyncio.TimeoutError:
            status, data = None, None
        if status != 200:
            raise NotFound('Could not get comic.')
        else:
            return data

    async def xkcd_insert(self, ctx, data):
        try:
            async with ctx.con.transaction():
                return await ctx.con.execute('''
                    INSERT INTO xkcd VALUES ($1, $2, $3, $4, $5)
                    ''', data['num'], data['safe_title'],
                    data['alt'], data['img'], xkcd_date(data))
        except asyncpg.UniqueViolationError:
            # got yesterday's comic
            pass

    @need_db
    @commands.command()
    async def xkcd(self, ctx, comic=''):
        """Get xkcd comics.

        [comic] can be the number of a comic or "r"/"rand"/"random"
        """
        data = None
        with ctx.typing():
            try:
                data = await self.fetch_xkcd(ctx, comic)
                if isinstance(data, dict):
                    await self.xkcd_insert(ctx, data)
            except NotFound as e:
                return await ctx.send(e)

            description = f'**Date:** {xkcd_date(data):%m/%d/%Y}\n{data["alt"]}'
            embed = discord.Embed(title=f'{data["num"]}: {data["safe_title"]}',
                                  url=make_xkcd_url(data['num'], api=False),
                                  description=description)
            embed.set_image(url=data['img'])
        await ctx.send(embed=embed)

    async def fetch_facts(self, count):
        status, data = await self.bot.request(FACTS.format(count=count))
        if status != 200:
            raise NotFound('No cat fact available.')
        return [d['fact'] for d in data['data']]

    async def fetch_cat(self):
        status, data = await self.bot.request('http://random.cat/meow')
        if status != 200:
            raise NotFound('Could not get cat.')
        return data['file']

    @commands.group(invoke_without_command=True)
    async def cat(self, ctx):
        """Get a random cat image."""
        with ctx.typing():
            try:
                image_url = await self.fetch_cat()
            except NotFound as e:
                return await ctx.send(e)

            try:
                fact = (await self.fetch_facts(1))[0]
            except NotFound as e:
                fact = ''

            embed = discord.Embed(description=fact or None)
            embed.set_image(url=image_url)
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            embed = discord.Embed(description=fact or None)
            embed.set_footer(text='Failed getting a cat image.')
            await ctx.send(embed=embed)

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
    async def cat_facts_error(self, ctx, exc):
        if isinstance(exc, commands.BadArgument):
            pass
        else:
            ctx.command = ctx.command.name


def setup(bot):
    bot.add_cog(Images(bot))
