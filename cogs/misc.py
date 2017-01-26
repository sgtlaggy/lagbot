from collections import OrderedDict
import unicodedata
import datetime
import asyncio
import random

from discord.ext import commands
import discord
import zenhan
import dice

from .utils.utils import integer, pluralize, say_and_pm
from .utils.emoji import digits, clocks
from .base import BaseCog


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


def die(arg):
    return (arg, dice.roll(arg))


class Misc(BaseCog):
    """Miscellaneous commands that don't fit in other categories."""
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

    @commands.command(aliases=['poll'], no_pm=True)
    @commands.bot_has_permissions(add_reactions=True)
    async def vote(self, ctx, *, options):
        """Allow users to vote on something.

        Usage:
        !poll Title Here
        Option 1
        Option ..
        Option 10

        For 30 seconds after creating a poll, you can add any :clockTIME: emoji to set the time.
        :clock1230: = 30 minutes
        :clock1:    = 1 hour
        :clock130:  = 1.5 hours
        :clock12:   = 12 hours
        You can also add the :x: emoji during this time to cancel the poll.

        Every vote session lasts 1 hour, unless otherwise set.
        Allows a maximum of 10 options.
        The poll creator can add the :x: emoji to end the poll early.
            The poll will end 30 seconds after adding it.
        """
        title, *options = [opt.strip() for opt in options.split('\n')]
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

        def react_check(reactions):
            def check(reaction, user):
                return (reaction.emoji in reactions and
                        reaction.message.id == poll_msg.id and
                        user.id == ctx.message.author.id)
            return check

        res = await self.bot.wait_for('reaction_add', timeout=30,
                                      check=react_check([*CLOCKS, '\N{CROSS MARK}']))
        if res is not None:
            if res[0].emoji == '\N{CROSS MARK}':
                await poll_msg.delete()
                return
            time_ind = CLOCKS.index(res[0].emoji)
            if time_ind % 2 == 1:
                poll_time = (int(time_ind / 2) + 1) * 60
            else:
                poll_time = 30
                while time_ind:
                    poll_time += 60
                    time_ind -= 2
        else:
            poll_time = 60
        res = await self.bot.wait_for('reaction_add',
                                      check=react_check(['\N{CROSS MARK}']),
                                      timeout=(poll_time * 60) - 30)
        if res is not None:
            await asyncio.sleep(30)
        poll_msg = await poll_msg.edit('***POLL IS CLOSED***\n' + poll_msg.content)
        reactions = [r for r in poll_msg.reactions if r.emoji in digits[1:]]
        win_score = max(r.count for r in reactions)
        if win_score == 1:
            await say_and_pm(ctx, f'No one voted on "{title}" {{channel}}')
            return
        else:
            winners = []
            for r in reactions:
                if r.count == win_score:
                    ind = digits.index(r.emoji)
                    winners.append(options[ind - 1])
            win_score -= 1
            if len(winners) == 1:
                await say_and_pm(ctx, pluralize('"{[0]}" won the poll "{}" {{channel}} with {} vote{{}}.'.format(
                    winners, title, win_score)))
            else:
                await say_and_pm(ctx, pluralize('The poll "{}" {{channel}} was a tie at {} vote{{}} between:\n{}'.format(
                    title, win_score, '\n'.join(winners))))

    @commands.command(no_pm=True)
    async def info(self, ctx, *, member: discord.Member = None):
        """Display information of specific user."""
        member = member or ctx.message.author
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

    @commands.command(aliases=['fullwidth', 'fw'])
    async def meme(self, ctx, *, chars):
        """Turn your lame normal text into full-width text."""
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send(zenhan.h2z(chars))


def setup(bot):
    bot.add_cog(Misc(bot))
