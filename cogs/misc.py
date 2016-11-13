from collections import OrderedDict
import unicodedata
import asyncio
import random

from discord.ext import commands

from .utils.utils import integer, plural, say_and_pm
from .utils.emoji import digits, clocks


CLOCKS = (clocks[-1], *clocks[:-1])

UNILINK = "http://www.fileformat.info/info/unicode/char/{}/index.htm"


def get_die(die):
    d = 'd' in die.lower()
    count, sides = 1, 6
    try:
        split = die.lower().split('d')
        if split[0]:
            count = int(split[0])
        if d:
            sides = int(split[1])
    except:
        raise commands.BadArgument('Invalid format: %s' % die)
    return (count, sides)


class Misc:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, *args: get_die):
        """In format XdY, rolls X dice each with Y sides.

        If X is neglected, it will be assumed to mean 1 die.
        You can also specify a list of dice to roll. "1d6 2d20 d12"
        """
        dice = args or [(1, 6)]
        dice_count = len(dice)
        msg = []
        for count, sides in dice:
            rolls = []
            for i in range(count):
                rolls.append(str(random.randint(1, sides)))
            if dice_count > 1:
                msg.append('d{}: {}'.format(sides, ', '.join(rolls)))
            else:
                msg.append(', '.join(rolls))
        if msg:
            await self.bot.say('\n'.join(msg))

    @roll.error
    async def roll_error(self, exc, ctx):
        if isinstance(exc, commands.BadArgument):
            await self.bot.say(str(exc))

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

    @commands.command(aliases=['poll'], pass_context=True, no_pm=True)
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
        You can also add the poop emoji during this time to cancel the poll.

        Every vote session lasts 1 hour, unless otherwise set.
        Allows a maximum of 10 options.
        The poll creator can add the poop emoji to end the poll early.
            The poll will end 30 seconds after adding it.
        """
        title, *options = options.split('\n')
        if len(options) > 10:
            await self.bot.say('Too many options.')
            return
        elif len(options) < 2:
            await self.bot.say('Too few options.')
            return

        msg = ['__' + title + '__']
        for num, opt in zip(digits[1:], options):
            msg.append('{} {}'.format(num, opt))
        poll_msg = await self.bot.say('\n'.join(msg))
        for ind in range(len(options)):
            await self.bot.add_reaction(poll_msg, digits[ind + 1])
        res = await self.bot.wait_for_reaction([*CLOCKS, '\N{PILE OF POO}'],
                                               user=ctx.message.author,
                                               message=poll_msg, timeout=30)
        if res is not None:
            if res.reaction.emoji == '\N{PILE OF POO}':
                await self.bot.delete_message(poll_msg)
                return
            time_ind = CLOCKS.index(res.reaction.emoji)
            if time_ind % 2 == 1:
                poll_time = (int(time_ind / 2) + 1) * 60
            else:
                poll_time = 30
                while time_ind:
                    poll_time += 60
                    time_ind -= 2
        else:
            poll_time = 60
        res = await self.bot.wait_for_reaction('\N{PILE OF POO}', message=poll_msg,
                                               user=ctx.message.author, timeout=(poll_time * 60) - 30)
        if res is not None:
            await asyncio.sleep(30)
        poll_msg = await self.bot.edit_message(poll_msg, '***POLL IS CLOSED***\n' + poll_msg.content)
        reactions = [r for r in poll_msg.reactions if r.emoji in digits[1:]]
        win_score = max(r.count for r in reactions)
        if win_score == 1:
            await say_and_pm(ctx, 'No one voted on "{}" {{channel}}'.format(title))
            return
        else:
            winners = []
            for r in reactions:
                if r.count == win_score:
                    ind = digits.index(r.emoji)
                    winners.append(options[ind - 1])
            win_score -= 1
            if len(winners) == 1:
                await say_and_pm(ctx, '"{[0]}" won the poll "{}" {{channel}} with {} vote{}.'.format(
                    winners, title, win_score, plural(win_score)))
            else:
                await say_and_pm(ctx, 'The poll "{}" {{channel}} was a tie at {} vote{} between:\n{}'.format(
                    title, win_score, plural(win_score), '\n'.join(winners)))

    @commands.command()
    async def charinfo(self, *, chars):
        """Get unicode character info."""
        msg = commands.Paginator(prefix='', suffix='')
        chars = unicodedata.normalize('NFC', chars)
        for char in chars:
            uc = hex(ord(char))[2:]
            msg.add_line('{char} - `{char}` - {name} - {link}'.format(
                name=unicodedata.name(char, '`U+%s`' % uc.upper()),
                char=char, link=UNILINK.format(uc)))
        for page in msg.pages:
            await self.bot.say(page)


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
