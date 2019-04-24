import traceback
import os

from discord.ext.commands import BadArgument
from discord.ext import commands


UPPER_PATH = os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0]


def rzip(*iterables):
    """Like builtin `zip`, but uses the right end of longer iterables instead of the left.

    Examples:
    rzip([1,2,3], [4,5]) -> ((2, 4), (3, 5))
    """
    lens = [len(it) for it in iterables]
    min_len = min(lens)
    diffs = [len_ - min_len for len_ in lens]
    return tuple(tuple(it[i + diffs[diff_ind]] for diff_ind, it in enumerate(iterables)) for i in range(min_len))


def pluralize(singular, plural, n, fmt='{n} {s}'):
    """Similar to `gettext.ngettext`, but returns a string including the number.

    `fmt` is an optional format string with fields `{n}` and `{s}` being replaced by
    the number and singular or plural string, respectively.

    Examples:
    pluralize('dog', 'dogs', 1)                -> '1 dog'
    pluralize('dog', 'dogs', 3)                -> '3 dogs'
    pluralize('dog', 'dogs', 3, '{n} ... {s}') -> 'dogs ... 3'
    """
    if n == 1:
        return fmt.format(n=n, s=singular)
    else:
        return fmt.format(n=n, s=plural)


def between(num, num_min, num_max, inclusive=True):
    """Make sure `num` is between `num_min` and `num_max`.

    Returns `num_max` if `num` is higher, `num_min` if `num` is lower.
    """
    if inclusive:
        if num > num_max:
            return num_max
        elif num < num_min:
            return num_min
    else:
        if num >= num_max:
            return num_max - 1
        elif num <= num_min:
            return num_min + 1
    return num


def integer(arg):
    """Attempts to return the arg converted to `int`.

    Returns nearest whole number if arg represents a `float`.
    Mainly to be used as typehint in commands.
    """
    try:
        int(arg)
    except ValueError:
        pass
    else:
        return int(arg)

    try:
        float(arg)
    except ValueError:
        pass
    else:
        return int(round(float(arg)))

    raise BadArgument('Converting to "int" failed.')


async def say_and_pm(ctx, content):
    """Send message to current channel as well as the command message's author.

    `ctx` can be either `discord.Message` or `commands.Context`
    """
    channel = ctx.channel
    author = ctx.author
    to_say = content.format(channel='')
    to_pm = content.format(channel=f'in {channel.mention}')
    return (await ctx.send(to_say),
            await author.send(to_pm))


def tb_args(exc):
    """Easily format arguments for `traceback` functions."""
    return (type(exc), exc, exc.__traceback__)


async def send_error(dest, ctx, exc, num):
    msg = f'{ctx.message.content}\nin {"guild" if ctx.guild else "DM"}'
    tb = ''.join(traceback.format_exception(*tb_args(exc))).replace(UPPER_PATH, '...')
    pag = commands.Paginator(prefix=f'{num} {msg}\n```')
    for line in tb.split('\n'):
        pag.add_line(line)
    for page in pag.pages:
        await dest.send(page)
