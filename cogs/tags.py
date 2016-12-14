import difflib

from discord.ext import commands
import asyncpg
import discord

from .utils.errors import NotInDB
from .utils.utils import plural
from .base import BaseCog


TAG_PREFIX = '%'


def lower(arg):
    return arg.lower().strip()


class Tags(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)

    def verify_name(self, name):
        if not name:
            raise ValueError('Tag name cannot be empty.')
        elif '@everyone' in name or '@here' in name:
            raise ValueError('Illegal tag name.')
        elif len(name) > 32:
            raise ValueError('Tag name too long.')
        elif name in self.tag.commands:
            raise ValueError('Cannot override subcommands.')

    async def get_tag(self, name):
        tag = await self.bot.db.fetchrow('''
            SELECT * FROM tags WHERE name = $1
            ''', name)
        if tag is not None:
            return tag
        tags = [r['name'] for r in await self.bot.db.fetch('SELECT name FROM tags')]
        matches = difflib.get_close_matches(name, tags)
        if not matches:
            raise NotInDB('Tag not found.')
        raise NotInDB('Tag not found. Did you mean...\n' + '\n'.join(matches))

    @commands.group(pass_context=True, invoke_without_command=True)
    async def tag(self, ctx, *, name: lower):
        """Get a tag.

        This can also be called with just %tagname
        """
        try:
            tag = await self.get_tag(name)
        except NotInDB as e:
            await self.bot.say(e)
            return
        await self.bot.say(tag['content'])
        async with self.bot.db.transaction():
            await self.bot.db.execute('''
                UPDATE tags SET uses = uses + 1 WHERE name = $1
                ''', tag['name'])
            await self.bot.db.execute('''
                INSERT INTO tagusers VALUES ($1)
                ON CONFLICT (id)
                DO UPDATE SET uses = tagusers.uses + 1
                ''', ctx.message.author.id)

    @tag.command(pass_context=True)
    async def create(self, ctx, name: lower, *, text):
        """Create a new tag.

        <name> must be wrapped in quotes if it contains a space.
        """
        try:
            self.verify_name(name)
        except ValueError as e:
            await self.bot.say(e)
            return
        try:
            async with self.bot.db.transaction():
                await self.bot.db.execute('''
                    INSERT INTO tags (name, content, owner_id, modified_at)
                    VALUES ($1, $2, $3, $4)
                    ''', name, text, ctx.message.author.id, ctx.message.timestamp)
        except asyncpg.UniqueViolationError:
            await self.bot.say('A tag with that name already exists!')
            return
        await self.bot.say('Created tag "{}".'.format(name))

    @tag.command(pass_context=True)
    async def rename(self, ctx, name: lower, *, new_name: lower):
        """Rename a tag you created.

        <name> must be wrapped in quotes if it contains a space.
        """
        try:
            tag = await self.get_tag(name)
            self.verify_name(new_name)
        except (NotInDB, ValueError) as e:
            await self.bot.say(e)
            return
        if ctx.message.author.id != tag['owner_id']:
            await self.bot.say("You don't own that tag.")
            return
        async with self.bot.db.transaction():
            await self.bot.db.execute('''
                UPDATE tags SET name = $1 WHERE name = $2
                ''', new_name, name)
        await self.bot.say('Renamed tag "{}" to "{}".'.format(name, new_name))

    @tag.command(pass_context=True)
    async def edit(self, ctx, name: lower, *, new_text):
        """Edit a tag you created.

        <name> must be wrapped in quotes if it contains a space.
        """
        try:
            tag = await self.get_tag(name)
        except NotInDB as e:
            await self.bot.say(e)
            return
        if ctx.message.author.id != tag['owner_id']:
            await self.bot.say("You don't own that tag.")
            return
        async with self.bot.db.transaction():
            await self.bot.db.execute('''
                UPDATE tags SET (content, modified_at) = ($1, $2)
                WHERE name = $3
                ''', new_text, ctx.message.timestamp, name)
        await self.bot.say('Updated tag "{}".'.format(name))

    @tag.command(pass_context=True)
    async def remove(self, ctx, *, name: lower):
        """Remove a tag you created."""
        try:
            tag = await self.get_tag(name)
        except NotInDB as e:
            await self.bot.say(e)
            return
        if ctx.message.author.id != tag['owner_id']:
            await self.bot.say("You don't own that tag.")
            return
        async with self.bot.db.transaction():
            await self.bot.db.execute('''
                DELETE FROM tags WHERE name = $1
                ''', name)
        await self.bot.say('Removed tag "{}".'.format(name))

    @tag.command()
    async def info(self, *, name: lower = None):
        """Get info about a tag or the tag DB.

        Get DB info by not specifying tag name.
        """
        if name is not None:
            try:
                tag = await self.get_tag(name)
            except NotInDB as e:
                await self.bot.say(e)
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
            embed.add_field(name='Total Tags', value=await self.bot.db.fetchval('''
                SELECT count(*) FROM tags
                '''))
            embed.add_field(name='Total Uses', value=await self.bot.db.fetchval('''
                SELECT sum(uses) FROM tagusers
                ''') or 0)
        await self.bot.say(embed=embed)

    @tag.command(pass_context=True)
    async def stats(self, ctx, *, member: discord.Member = None):
        """See stats about your own or another person's tag usage."""
        if member is None:
            member = ctx.message.author
        tags = await self.bot.db.fetchval('''
            SELECT count(*) FROM tags WHERE owner_id = $1
            ''', member.id)
        uses = await self.bot.db.fetchval('''
            SELECT uses FROM tagusers WHERE id = $1
            ''', member.id) or 0
        embed = discord.Embed()
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        embed.add_field(name='Tags Created', value=tags)
        embed.add_field(name='Tags Used', value=uses)
        await self.bot.say(embed=embed)

    @tag.command(name='list', pass_context=True)
    async def _list(self, ctx, *, member: discord.Member = None):
        """See tags you or another person created."""
        if member is None:
            member = ctx.message.author
            mention = 'You have'
        else:
            mention = '{.mention} has'.format(member)
        tags = await self.bot.db.fetch('''
            SELECT name FROM tags WHERE owner_id = $1
            ''', member.id)
        if not tags:
            await self.bot.say(mention + ' no tags.')
            return
        messages = [['{} {} tag{}:'.format(mention, len(tags), plural(len(tags))), '']]
        for tag in tags:
            if sum(messages[-1], key=len) + len(', ' + tag) > 2000:
                messages.append([tag])
            else:
                messages[-1][-1] += ', ' + tag

    @tag.command(pass_context=True)
    async def leaderboard(self, ctx):
        """See leaderboard of most used tags and largest users of tags."""
        tags = await self.bot.db.fetch('''
            SELECT name, uses FROM tags ORDER BY uses DESC LIMIT 5
            ''')
        userstats = await self.bot.db.fetch('''
            SELECT id, uses FROM tagusers ORDER BY uses DESC LIMIT 10
            ''')
        users = []
        for r in userstats:
            users.append((await self.bot.get_user_info(r['id']), r['uses']))
        embed = discord.Embed()
        embed.add_field(name='Users', value='\n'.join(['{.mention} - {}'.format(user, uses)
                                                       for user, uses in users]) or 'None')
        embed.add_field(name='Tags', value='\n'.join(['{0[name]} - {0[uses]}'.format(r)
                                                      for r in tags]) or 'None')
        await self.bot.say(embed=embed)

    async def on_message(self, message):
        if message.content.startswith(TAG_PREFIX):
            ctx = commands.Context(bot=self.bot,
                                   invoked_with=TAG_PREFIX,
                                   message=message,
                                   view=commands.view.StringView(message.content[len(TAG_PREFIX):]),
                                   prefix=TAG_PREFIX)
            await self.tag.invoke(ctx)


def setup(bot):
    bot.add_cog(Tags(bot))
