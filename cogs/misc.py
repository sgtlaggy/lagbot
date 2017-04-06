from collections import OrderedDict
import unicodedata
import datetime
import asyncio
import random
import re

from discord.ext import commands
import discord
import zenhan
import dice

from utils.utils import integer, pluralize, db_encode, db_decode
from utils.emoji import digits, clocks
from utils.checks import need_db
from cogs.base import BaseCog


time_re = re.compile(r"(?:(?P<days>[0-9]{1,2})d)?(?:(?P<hours>[0-9]{1,2})h)?(?:(?P<minutes>[0-9]{1,2})m)?$")
TIMER_SLEEP = 301
CLOCKS = (clocks[-1], *clocks[:-1])

UNILINK = "http://www.fileformat.info/info/unicode/char/{}/index.htm"


def fancy_time(orig_time, utc=False):
    diff = datetime.datetime.utcnow() - orig_time
    nice = ''
    if diff.days >= 365:
        years = diff.days // 365
        nice += pluralize(f'{years} year{{}}, ')
    days = diff.days % 365
    nice += pluralize(f'{days} day{{}} ago')
    if utc:
        nice += f' ({orig_time} UTC)'
    else:
        nice += f' ({orig_time:%Y-%m-%d})'
    return nice


def seconds(arg):
    match = time_re.match(arg)
    total_seconds = 0
    if match is None or not match.group(0):
        raise commands.BadArgument("Couldn't parse time.")
    days, hours, minutes = match.group('days', 'hours', 'minutes')
    if days:
        total_seconds += int(days) * 24 * 60 * 60
    if hours:
        total_seconds += int(hours) * 60 * 60
    if minutes:
        total_seconds += int(minutes) * 60
    if total_seconds < (TIMER_SLEEP - 1):
        raise commands.UserInputError('Time is too short.')
    return total_seconds


def die(arg):
    return (arg, dice.roll(arg))


class Misc(BaseCog):
    """Miscellaneous commands that don't fit in other categories."""
    def __init__(self, bot):
        super().__init__(bot)
        if not self.bot._debug:
            self.timer_task = self.bot.loop.create_task(self.timers())

    @commands.command(name='roll')
    async def roll_dice(self, ctx, *rolls: die):
        """In format CdS, rolls C dice each with S sides.

        If C is neglected, it will be assumed to mean 1 die.

        Advanced notation:
            * add "t" to get the total of the rolls : 2d6t   -> 9
            * add "s" to sort the rolls             : 2d6s   -> 2, 4
            * add "^X" to keep the highest X rolls  : 10d6^3 -> 4, 4, 5
            * add "vX" to keep the lowest X rolls   : 10d6v3 -> 1, 2, 2

        You can also specify a list of dice to roll. "1d6 2d20 d12"

        This command also handles basic arithmetic operations (/*+-)
        """
        rolls = rolls or [('1d6', random.randint(1, 6))]
        msg = []
        for roll, result in rolls:
            if isinstance(result, list):
                result = ', '.join(map(str, result))
            msg.append(f'{roll}: {result}')
        await ctx.send('\n'.join(msg))

    @roll_dice.error
    async def roll_error(self, exc, ctx):
        if isinstance(exc, commands.BadArgument):
            await ctx.send(str(exc))

    @commands.command()
    async def flip(self, ctx, coins: integer = 1):
        """Flip any number of coins."""
        coins = coins if coins >= 1 else 1
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
                message.append(f'{f}: {c}')
        message = '\n'.join(message)
        await ctx.send(message)

    @commands.command()
    async def choose(self, ctx, *options):
        """Choose a random element from a list of items.

        Any item that contains a space must be wrapped in double quotes (").
        """
        if len(options) == 0:
            await ctx.send('No.')
        else:
            await ctx.send(random.choice(options))

    @commands.command()
    @commands.guild_only()
    async def info(self, ctx, *, member: discord.Member = None):
        """Display information of specific user."""
        member = member or ctx.author
        roles = [f'@{role}' for role in member.roles if role.name != '@everyone']
        embed = discord.Embed(colour=member.colour)
        embed.add_field(name='Name', value=member.name)
        embed.add_field(name='Tag', value=member.discriminator)
        embed.add_field(name='ID', value=member.id)
        embed.add_field(name='Joined Server', value=fancy_time(member.joined_at)[::-1].replace(' ', '\n', 1)[::-1])
        embed.add_field(name='Joined Discord', value=fancy_time(member.created_at)[::-1].replace(' ', '\n', 1)[::-1])
        embed.add_field(name='Roles', value=' '.join(roles))
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def charinfo(self, ctx, *, chars):
        """Get unicode character info."""
        if not chars:
            return
        chars = unicodedata.normalize('NFC', chars)
        if len(chars) > 25:
            await ctx.send('Too many emoji.')
            return
        embed = discord.Embed()
        for char in chars:
            uc = hex(ord(char))[2:]
            name = unicodedata.name(char, 'unknown')
            if name in {'SPACE', 'EM QUAD', 'EN QUAD'} or ' SPACE' in name:
                char = '" "'
            short = len(uc) <= 4
            code = f'`\\{"u" if short else "U"}{uc.lower().zfill(4 if short else 8)}`'
            embed.add_field(name=name, value=f'{char} [{code}]({UNILINK.format(uc)})')
        await ctx.send(embed=embed)

    @commands.command(aliases=['fw'])
    async def fullwidth(self, ctx, *, chars):
        """Turn your lame normal text into full-width text."""
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send(zenhan.h2z(chars))

    @need_db
    @commands.group(aliases=['vote'], invoke_without_command=True,
                    usage='[time] <title>\n<option 1>\n[option ..]\n[option 10]')
    @commands.guild_only()
    @commands.bot_has_permissions(add_reactions=True)
    async def poll(self, ctx, *, options):
        """Allow users to vote on something.

        [time] must be in the form "1d2h3m" (1 day, 2 hours, 3 minutes) if provided.
        At least one of "#d", "#h", or "#m" must be provided.

        Every vote session lasts 1 hour, unless otherwise set.
        Minimum time is 5 minutes, maximum time is 7 days.
        Allows a maximum of 10 options.
        """
        title, *options = [opt.strip() for opt in options.split('\n')]
        try:
            time = seconds(title.split()[0])
        except commands.BadArgument:
            time = 60 * 60
        else:
            title = ' '.join(title.split()[1:])
        if time > 7 * 24 * 60 * 60:
            await ctx.send('Requested time too long, cancelling poll.')
            return

        if len(options) > 10:
            await ctx.send('Too many options.')
            return
        elif len(options) < 2:
            await ctx.send('Too few options.')
            return

        msg = ['__' + title + '__']
        for num, opt in zip(digits[1:], options):
            msg.append(f'{num} {opt}')
        poll_msg = await ctx.send('\n'.join(msg))
        for ind in range(len(options)):
            await poll_msg.add_reaction(digits[ind + 1])
        end_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=time)
        encoded_options = [db_encode(option) for option in options]
        async with ctx.con.transaction():
            await ctx.con.execute('''
                INSERT INTO polls (message_id, channel_id, author_id, title, options, end_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ''', poll_msg.id, ctx.channel.id, ctx.author.id,
                     db_encode(title), encoded_options, end_at)  # NOQA
        await ctx.author.send(f'The ID for poll "{title}" in {ctx.channel.mention} is {poll_msg.id}')

    @need_db
    @poll.command()
    async def end(self, ctx, *, poll_id: int):
        """End a poll you created.

        <poll_id> is the ID that was sent to you in a DM.

        The poll will end 5 minutes after using this command.
        """
        rec = await ctx.con.fetchrow('''
            SELECT * FROM polls WHERE message_id = $1
            ''', poll_id)
        if rec is None:
            await ctx.send('There is no running poll with that ID.')
            return
        if int(rec['author_id']) != ctx.author.id:
            await ctx.send('You did not start that poll.')
            return
        end_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=300)
        async with ctx.con.transaction():
            await ctx.con.execute('''
                UPDATE polls SET end_at = $1 WHERE message_id = $2
                ''', end_at, poll_id)
        title = db_decode(rec['title'])
        await ctx.send(f'Poll "{title}" will end in 5 minutes.')

    @need_db
    @poll.command()
    async def cancel(self, ctx, *, poll_id: int):
        """Cancel a poll you created.

        <poll_id> is the ID that was sent to you in a DM.
        """
        rec = await ctx.con.fetchrow('''
            SELECT * FROM polls WHERE message_id = $1
            ''', poll_id)
        if rec is None:
            await ctx.send('There is no running poll with that ID.')
            return
        if int(rec['author_id']) != ctx.author.id:
            await ctx.send('You did not start that poll.')
            return
        async with ctx.con.transaction():
            await ctx.con.execute('''
                UPDATE polls SET cancelled = TRUE WHERE message_id = $1
                ''', poll_id)
        channel = self.bot.get_channel(int(rec['channel_id']))
        if channel is not None:
            message = await channel.get_message(int(rec['message_id']))
            await message.delete()
        title = db_decode(rec['title'])
        await ctx.send(f'Poll "{title}" has been cancelled.')

    @need_db
    @commands.command(aliases=['remindme', 'timer'])
    async def reminder(self, ctx, time: seconds, *, content):
        """Set a reminder for yourself some time in the future.

        <time> must be provided in the form "1d2h3m" (1 day, 2 hours, 3 minutes)
        At least one of "#d", "#h", or "#m" must be provided.

        Minimum time is 5 minutes, maximum time is 14 days.
        """
        if time > 14 * 24 * 60 * 60:
            await ctx.send('Requested time too long, cancelling reminder.')
            return
        end_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=time)
        async with ctx.con.transaction():
            await ctx.con.execute('''
                INSERT INTO reminders (message_id, channel_id, author_id, content, end_at)
                VALUES ($1, $2, $3, $4, $5)
                ''', ctx.message.id, ctx.channel.id, ctx.author.id,
                     db_encode(content), end_at)  # NOQA
        await ctx.send(f"I'll remind you about \"{content}\" in {time} seconds.")

    @poll.error
    @reminder.error
    async def reminder_error(self, exc, ctx):
        actual_exc = getattr(exc, 'original', exc)
        if isinstance(actual_exc, commands.UserInputError):
            exc.handled = True
            await ctx.send(actual_exc)

    async def delete_timer(self, rec, table):
        async with self.bot.db_pool.acquire() as con:
            async with con.transaction():
                res = await con.execute(f'''
                    DELETE FROM {table} WHERE message_id = $1
                    ''', rec['message_id'])
        return int(res[-1])

    async def get_data(self, rec):
        channel = self.bot.get_channel(int(rec['channel_id']))
        if isinstance(channel, discord.GroupChannel):
            author = discord.utils.get(channel.recipients, id=int(rec['author_id']))
        elif isinstance(channel, discord.DMChannel):
            author = channel.recipient
        else:
            author = discord.utils.get(channel.members, id=int(rec['author_id']))
        return channel, author

    async def finish_reminder(self, rec):
        try:
            channel, author = await self.get_data(rec)
        except AttributeError:
            return await self.delete_timer(rec, 'reminders')
        content = db_decode(rec['content'])
        if author is None:
            author = await self.bot.get_user_info(int(rec['author_id']))
            channel = author
        if datetime.datetime.utcnow() < rec['end_at']:
            diff = rec['end_at'] - datetime.datetime.utcnow()
            await asyncio.sleep(diff.total_seconds(), loop=self.bot.loop)
        await channel.send(f'{author.mention}, you asked to be reminded about "{content}"')
        await self.delete_timer(rec, 'reminders')

    async def finish_poll(self, rec):
        try:
            channel, author = await self.get_data(rec)
        except AttributeError:
            return await self.delete_timer(rec, 'polls')
        message = await channel.get_message(int(rec['message_id']))
        if message is None:
            await self.delete_timer(rec, 'polls')
            return
        if datetime.datetime.utcnow() < rec['end_at']:
            diff = rec['end_at'] - datetime.datetime.utcnow()
            await asyncio.sleep(diff.total_seconds(), loop=self.bot.loop)
        async with self.bot.db_pool.acquire() as con:
            rec = await con.fetchrow('''
                SELECT * FROM polls WHERE message_id = $1
                ''', rec['message_id'])
        if rec['cancelled']:
            return await self.delete_timer(rec, 'polls')
        author = author or await self.bot.get_user_info(int(rec['author_id']))
        await message.edit(content='***POLL IS CLOSED***\n' + message.content)
        title = db_decode(rec['title'])
        options = [db_decode(option) for option in rec['options']]
        reactions = [r for r in message.reactions if r.emoji in digits[1:]]
        win_score = max(r.count for r in reactions)
        if win_score == 1:
            await channel.send(f'No one voted on "{title}"')
            await author.send(f'No one voted on "{title}" in {channel.mention}.')
            return
        else:
            winners = []
            for r in reactions:
                if r.count == win_score:
                    ind = digits.index(r.emoji)
                    winners.append(options[ind - 1])
            win_score -= 1
            if len(winners) == 1:
                await channel.send(pluralize('"{[0]}" won the poll "{}" with {} vote{{}}.'.format(
                    winners, title, win_score)))
                await author.send(pluralize('"{[0]}" won the poll "{}" in {.mention} with {} vote{{}}.'.format(
                    winners, title, channel, win_score)))
            else:
                await channel.send(pluralize('The poll "{}" was a tie at {} vote{{}} between:\n{}'.format(
                    title, win_score, '\n'.join(winners))))
                await author.send(pluralize('The poll "{}" in {.mention} was a tie at {} vote{{}} between:\n{}'.format(
                    title, channel, win_score, '\n'.join(winners))))
        await self.delete_timer(rec, 'polls')

    async def timers(self):
        """Background task to check for past/upcoming reminders or polls."""
        await self.bot.wait_until_ready()
        delta = datetime.timedelta(seconds=TIMER_SLEEP - 1)
        while not self.bot.is_closed():
            async with self.bot.db_pool.acquire() as con:
                upcoming_reminders = await con.fetch('''
                    SELECT * FROM reminders WHERE end_at <= ((now() at time zone 'utc') + $1)
                    ''', delta)
                upcoming_polls = await con.fetch('''
                    SELECT * FROM polls WHERE end_at <= ((now() at time zone 'utc') + $1)
                    ''', delta)
            upcoming = [*[self.finish_reminder(rec) for rec in upcoming_reminders],
                        *[self.finish_poll(rec) for rec in upcoming_polls]]
            if upcoming:
                await asyncio.gather(*upcoming, loop=self.bot.loop)
            await asyncio.sleep(TIMER_SLEEP, loop=self.bot.loop)

    def __unload(self):
        try:
            self.timer_task.cancel()
        except AttributeError:
            pass


def setup(bot):
    bot.add_cog(Misc(bot))
