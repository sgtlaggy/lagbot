from collections import OrderedDict
import asyncio
import random

from discord.ext import commands

from .utils.utils import integer, plural
from .utils.emoji import digits, clocks


CLOCKS = (clocks[-1], *clocks[:-1])


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

    @commands.command(aliases=['poll'], pass_context=True, no_pm=True)
    @commands.bot_has_permissions(add_reactions=True)
    async def vote(self, ctx, title, *options):
        """Allow users to vote on something.

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

        <title> must be wrapped with double quotes (") if it contains a space
        [options...] must be wrapped in double quotes if they contain spaces
        """
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
            await self.bot.say('No one voted on "{}"'.format(title))
            return
        else:
            winners = []
            for r in reactions:
                if r.count == win_score:
                    ind = digits.index(r.emoji)
                    winners.append(options[ind - 1])
            win_score -= 1
            if len(winners) == 1:
                await self.bot.say('"{[0]}" won the poll "{}" with {} vote{}.'.format(
                    winners, title, win_score, plural(win_score)))
            else:
                await self.bot.say('The poll "{}" was a tie at {} vote{} between:\n{}'.format(
                    title, win_score, plural(win_score), '\n'.join(winners)))


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Misc(bot))
