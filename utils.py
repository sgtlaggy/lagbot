import os

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


def tb_args(exc):
    """Easily format arguments for `traceback` functions."""
    return (type(exc), exc, exc.__traceback__)


def commaize(seq):
    seq = tuple(seq)
    length = len(seq)
    if length == 0:
        return ''
    if length == 1:
        return seq[0]
    elif length == 2:
        return ' and '.join(seq)
    else:
        return ', and '.join([', '.join(seq[:-1]), seq[-1]])


def clamp(value, low=None, high=None):
    if low is not None and value < low:
        value = low
    elif high is not None and value > high:
        value = high
    return value
