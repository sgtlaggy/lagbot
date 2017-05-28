import difflib

from discord.ext import commands
import asyncpg
import discord

from utils.utils import pluralize, db_encode, db_decode
from utils.checks import need_db
from utils.errors import NotInDB
from cogs.base import BaseCog
from utils import checks


TAG_PREFIX = '%'


def lower(arg):
    return arg.lower().strip()


class Tags(BaseCog):
    """Commands related to tags."""
    def verify_name(self, name):
        if not name:
            raise ValueError('Tag name cannot be empty.')
        elif any(illegal in name for illegal in {'@everyone', '@here'}):
            raise ValueError('Illegal tag name.')
        elif len(name) > 32:
            raise ValueError('Tag name too long.')
        elif name in self.tag.commands:
            raise ValueError('Cannot override subcommands.')

    async def get_tag(self, ctx, name):
        tag = await ctx.con.fetchrow('''
            SELECT * FROM tags WHERE name = $1
            ''', name)
        if tag is not None:
            return tag
        async with ctx.con.transaction():
            tags = [r['name'] async for r in ctx.con.cursor('SELECT name FROM tags')]
        matches = difflib.get_close_matches(name, tags)
        if not matches:
            raise NotInDB('Tag not found.')
        raise NotInDB('Tag not found. Did you mean...\n' + '\n'.join(matches))

    async def update_uses(self, ctx, tag):
        if isinstance(tag, str):
            name = tag
        else:
            name = tag['name']
        async with ctx.con.transaction():
            await ctx.con.execute('''
                UPDATE tags SET uses = uses + 1 WHERE name = $1
                ''', name)

    @need_db
    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name: lower):
        """Get a tag.

        This can also be called with just %tagname
        """
        try:
            tag = await self.get_tag(ctx, name)
        except NotInDB as e:
            await ctx.send(e)
            return
        await ctx.send(db_decode(tag['content']))
        await self.update_uses(ctx, tag)

    @need_db
    @tag.command()
    async def random(self, ctx):
        """Get a random tag."""
        tag = await ctx.con.fetchrow('''
            SELECT * FROM tags ORDER BY random() LIMIT 1
            ''')
        if tag is None:
            await ctx.send('No tags in db.')
            return
        await ctx.send(db_decode(tag['content']))
        await self.update_uses(ctx, tag)

    @need_db
    @tag.command()
    async def create(self, ctx, name: lower, *, text):
        """Create a new tag.

        <name> must be wrapped in quotes if it contains a space.
        """
        try:
            self.verify_name(name)
        except ValueError as e:
            await ctx.send(e)
            return
        try:
            async with ctx.con.transaction():
                await ctx.con.execute('''
                    INSERT INTO tags (name, content, owner_id)
                    VALUES ($1, $2, $3)
                    ''', name, db_encode(text), ctx.author.id)
        except asyncpg.UniqueViolationError:
            await ctx.send('A tag with that name already exists!')
            return
        await ctx.send(f'Created tag "{name}".')

    @need_db
    @tag.command()
    async def rename(self, ctx, name: lower, *, new_name: lower):
        """Rename a tag you created.

        <name> must be wrapped in quotes if it contains a space.
        """
        try:
            tag = await self.get_tag(ctx, name)
            self.verify_name(new_name)
        except (NotInDB, ValueError) as e:
            await ctx.send(e)
            return
        if ctx.author.id != tag['owner_id']:
            await ctx.send("You don't own that tag.")
            return
        async with ctx.con.transaction():
            await ctx.con.execute('''
                UPDATE tags SET name = $1 WHERE name = $2
                ''', new_name, name)
        await ctx.send(f'Renamed tag "{name}" to "{new_name}".')

    @need_db
    @tag.command()
    async def edit(self, ctx, name: lower, *, new_text):
        """Edit a tag you created.

        <name> must be wrapped in quotes if it contains a space.
        """
        try:
            tag = await self.get_tag(ctx, name)
        except NotInDB as e:
            await ctx.send(e)
            return
        if ctx.author.id != tag['owner_id']:
            await ctx.send("You don't own that tag.")
            return
        async with ctx.con.transaction():
            await ctx.con.execute('''
                UPDATE tags SET (content, modified_at) = ($1, $2)
                WHERE name = $3
                ''', db_encode(new_text), ctx.message.created_at, name)
        await ctx.send(f'Updated tag "{name}".')

    @need_db
    @tag.command()
    async def remove(self, ctx, *, name: lower):
        """Remove a tag you created."""
        try:
            tag = await self.get_tag(ctx, name)
        except NotInDB as e:
            await ctx.send(e)
            return
        if ctx.author.id != tag['owner_id']:
            await ctx.send("You don't own that tag.")
            return
        async with ctx.con.transaction():
            await ctx.con.execute('''
                DELETE FROM tags WHERE name = $1
                ''', name)
        await ctx.send(f'Removed tag "{name}".')

    @need_db
    @tag.command()
    async def info(self, ctx, *, name: lower = None):
        """Get info about a tag or the tag DB.

        Get DB info by not specifying tag name.
        """
        if name is not None:
            try:
                tag = await self.get_tag(ctx, name)
            except NotInDB as e:
                await ctx.send(e)
                return
            embed = discord.Embed(title=name)
            owner = await self.bot.get_user_info(tag['owner_id'])
            embed.set_author(name=str(owner), icon_url=owner.avatar_url)
            embed.add_field(name='Owner', value=owner.mention)
            embed.add_field(name='Uses', value=tag['uses'])
            embed.set_footer(text='Last modified')
            embed.timestamp = tag['modified_at']
        else:
            embed = discord.Embed(title='DB Info')
            embed.add_field(name='Total Tags', value=await ctx.con.fetchval('''
                SELECT count(*) FROM tags
                '''))
            embed.add_field(name='Total Uses', value=await ctx.con.fetchval('''
                SELECT sum(uses) FROM tags
                ''') or 0)
        await ctx.send(embed=embed)

    @need_db
    @tag.command(name='list')
    async def list_(self, ctx, *, member: discord.Member = None):
        """See tags you or another person created."""
        if member is None:
            member = ctx.author
            mention = 'You have'
        else:
            mention = f'{member.mention} has'
        tags = await ctx.con.fetch('''
            SELECT name FROM tags WHERE owner_id = $1
            ''', member.id)
        if not tags:
            await ctx.send(mention + ' no tags.')
            return
        messages = [[pluralize(f'{mention} {len(tags)} tag{{}}:'), '']]
        for tag in tags:
            if sum(len(m) for m in messages[-1]) + len(', ' + tag['name']) > 2000:
                messages.append([tag['name']])
            elif len(messages[-1][-1]) == 0:
                messages[-1][-1] = tag['name']
            else:
                messages[-1][-1] += ', ' + tag['name']
        for message in messages:
            await ctx.send('\n'.join(message))

    @need_db
    @tag.command()
    async def leaderboard(self, ctx):
        """See leaderboard of most used tags."""
        tags = await ctx.con.fetch('''
            SELECT name, uses FROM tags ORDER BY uses DESC LIMIT 10
            ''')
        embed = discord.Embed()
        embed.add_field(name='Tags', value='\n'.join([f'{r["name"]} - {r["uses"]}' for r in tags]) or 'None')
        await ctx.send(embed=embed)

    @need_db
    @tag.command(usage='<off|on>')
    @checks.owner_or_permissions(manage_guild=True)
    async def prefix(self, ctx, allow: bool):
        """Allow or disallow usage of short (%) prefix for tags."""
        async with ctx.con.transaction():
            if allow:
                res = await ctx.con.execute('''
                    DELETE FROM noshorttag WHERE guild_id = $1
                    ''', ctx.guild.id)
                if res[-1] == '0':
                    await ctx.send('Short prefix is already enabled.')
                else:
                    await ctx.send('Short prefix is now enabled.')
            else:
                try:
                    res = await ctx.con.execute('''
                        INSERT INTO noshorttag (guild_id) VALUES ($1)
                        ''', ctx.guild.id)
                except asyncpg.UniqueViolationError:
                    await ctx.send('Short prefix is already disabled.')
                else:
                    await ctx.send('Short prefix is now disabled.')

    async def on_message(self, message):
        if self.bot._debug:
            return
        if message.guild is not None:
            async with self.bot.db_pool.acquire() as con:
                no_short = await con.fetchval('''
                    SELECT EXISTS(SELECT * FROM noshorttag WHERE guild_id = $1)
                    ''', message.guild.id)
            if no_short:
                return
        if message.content.startswith(TAG_PREFIX):
            tag = message.content[len(TAG_PREFIX):]
            ctx = commands.Context(bot=self.bot,
                                   invoked_with=TAG_PREFIX,
                                   message=message,
                                   view=commands.view.StringView(tag),
                                   prefix=TAG_PREFIX)
            await self.tag.invoke(ctx)


def setup(bot):
    bot.add_cog(Tags(bot))
