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
            continue
        elif word.endswith('{}'):
            if last_num is None:
                last_num = 1
            plurals.append(plural(last_num))
    return s.format(*plurals)


def between(num, num_min, num_max, inclusive=True):
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
    channel = ctx.message.channel
    author = ctx.message.author
    to_say = content.format(channel='')
    to_pm = content.format(channel=f'in {channel.mention}')
    return (await ctx.send(to_say),
            await author.send(to_pm))


def tb_args(exc):
    return (type(exc), exc, exc.__traceback__)
