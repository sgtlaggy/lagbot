from discord.ext.commands import BadArgument


TIME_BRIEF = ('{d}d', '{h}h', '{m}m', '{s}s')
TIME_LONG = ('{d} day{dp}', '{h} hour{hp}', '{m} minute{mp}', '{s} second{sp}')


def plural(num):
    return 's' if num != 1 else ''


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
    to_pm = content.format(channel='in %s' % channel.mention)
    await ctx.bot.send_message(channel, to_say)
    await ctx.bot.send_message(author, to_pm)


def tb_args(self, exc):
    return (type(exc), exc, exc.__traceback__)
