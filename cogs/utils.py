"""Module for miscellaneous functions used by more than one cog/module."""


def list_align(words, extra=0):
    """Find word of greatest length and return list of differences in length.

    Arguments:
    words -- list of words

    Returns:
    lens -- list of ints
    """
    longest = 0
    lens = []
    for word in words:
        if len(word) > longest:
            longest = len(word)
    for word in words:
        lens.append(longest - len(word))
    lens = [space + extra for space in lens]
    return lens
