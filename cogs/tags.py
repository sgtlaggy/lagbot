import difflib

from discord.ext import commands
import asyncpg
import discord

from utils.utils import pluralize, db_encode, db_decode
from utils.checks import need_db
from utils.errors import NotInDB
from cogs.base import BaseCog


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
        tags = [r['name'] for r in await ctx.con.fetch('SELECT name FROM tags')]
        matches = difflib.get_close_matches(name, tags)
        if not matches:
            raise NotInDB('Tag not found.')
        raise NotInDB('Tag not found. Did you mean...\n' + '\n'.join(matches))

    async def update_uses(self, ctx, tag):
        user = ctx.author
        if isinstance(tag, str):
            name = tag
        else:
            name = tag['name']
        async with ctx.con.transaction():
            await ctx.con.execute('''
                UPDATE tags SET uses = uses + 1 WHERE name = $1
                ''', name)
            await ctx.con.execute('''
                INSERT INTO tagusers VALUES ($1)
                ON CONFLICT (id)
                DO UPDATE SET uses = tagusers.uses + 1
                ''', user.id)

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
                SELECT sum(uses) FROM tagusers
                ''') or 0)
        await ctx.send(embed=embed)

    @need_db
    @tag.command()
    async def stats(self, ctx, *, member: discord.Member = None):
        """See stats about your own or another person's tag usage."""
        if member is None:
            member = ctx.author
        tags = await ctx.con.fetchval('''
            SELECT count(*) FROM tags WHERE owner_id = $1
            ''', member.id)
        uses = await ctx.con.fetchval('''
            SELECT uses FROM tagusers WHERE id = $1
            ''', member.id) or 0
        embed = discord.Embed()
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        embed.add_field(name='Tags Created', value=tags)
        embed.add_field(name='Tags Used', value=uses)
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
        """See leaderboard of most used tags and largest users of tags."""
        tags = await ctx.con.fetch('''
            SELECT name, uses FROM tags ORDER BY uses DESC LIMIT 10
            ''')
        userstats = await ctx.con.fetch('''
            SELECT id, uses FROM tagusers ORDER BY uses DESC LIMIT 10
            ''')
        users = []
        for r in userstats:
            users.append((await self.bot.get_user_info(r['id']), r['uses']))
        embed = discord.Embed()
        embed.add_field(name='Users', value='\n'.join([f'{user.mention} - {uses}'
                                                       for user, uses in users]) or 'None')
        embed.add_field(name='Tags', value='\n'.join([f'{r["name"]} - {r["uses"]}'
                                                      for r in tags]) or 'None')
        await ctx.send(embed=embed)

    async def on_message(self, message):
        if self.bot._debug or message.guild.id == 110373943822540800:  # DiscordBots server
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
