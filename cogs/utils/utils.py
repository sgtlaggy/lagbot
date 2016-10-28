from discord.ext.commands import BadArgument


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
    if arg.isdigit():
        return int(arg)
    elif '.' in arg and all(n.isdigit() for n in arg.split('.')):
        return int(arg.split('.')[0])
    else:
        raise BadArgument('Converting to "int" failed.')
