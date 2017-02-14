import base64

from discord.ext.commands import BadArgument


TIME_BRIEF = ('{d}d', '{h}h', '{m}m', '{s}s')
TIME_LONG = ('{d} day{{}}', '{h} hour{{}}', '{m} minute{{}}', '{s} second{{}}')


def plural(num):
    return 's' if num != 1 else ''


def pluralize(s):
    """Takes a string and returns it with pluralized words.

    Any space that should be pluralized should be marked with '{}'
    If '{}' appears before any numbers, it will be set to an empty string.

    Examples:
    pluralize(f'{count} dog{{}}') -> '1 dog' / '2 dogs'
    """
    last_num = None
    plurals = []
    for word in s.split():
        if word.isdigit():
            last_num = int(word)
        elif '{}' in word:
            if last_num is None:
                last_num = 1
            plurals.append(plural(last_num))
    return s.format(*plurals)


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
    """Send message to current channel as well as the command message's author."""
    channel = ctx.message.channel
    author = ctx.message.author
    to_say = content.format(channel='')
    to_pm = content.format(channel=f'in {channel.mention}')
    return (await ctx.send(to_say),
            await author.send(to_pm))


def tb_args(exc):
    """Easily format arguments for `traceback` functions."""
    return (type(exc), exc, exc.__traceback__)


# Postgres keeps seeing `b64encode(text.encode())` as `text` even though it's
# `bytea`, so the `.encode()).decode()` is to store base64 with no headaches
# These functions are mainly for not destroying terminal output when viewing
# table contents that may contain emoji.
def db_encode(text):
    return base64.b64encode(text.encode()).decode()


def db_decode(text):
    return base64.b64decode(text.encode()).decode()
