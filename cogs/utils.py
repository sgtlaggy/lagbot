"""General helper functions."""


def func_desc(func):
    """Get first sentence/description of function from docstring.

    Arguments:
    func -- function to get description from

    Returns:
    str -- "No description." or first sentence of docstring
    """
    doc = func.__doc__
    if doc is None:
        return 'No description.'
    desc = ''
    for c in doc:
        if c == '\n':
            desc += ' '
        desc += c
        if c == '.':
            break
    return desc


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


def is_url(text):
    """Check if a string is a standard http(s) URL."""
    if text.startswith('http:') or text.startswith('https:'):
        return True
    return False


def stream_name_link(nl):
    """Get stream link from name or vice-versa."""
    if is_url(nl):
        link = nl
        name = link.split('/')[-1]
    else:
        name = nl
        link = 'http://twitch.tv/{}'.format(name.lower())
    return name, link


def unformat_str(raw):
    """Make a string discord-friendly."""
    new = ''
    rep = ['_', '*', '`', '~']
    for c in raw:
        if c in rep:
            new += '\\'
        new += c
    return new


def stream_message(*args):
    """Get message in stream announcement."""
    message = ''
    if '#' in args:
        for i, a in enumerate(args):
            if a == '#':
                message = '@everyone ' + ' '.join(args[i + 1:])
                break
    elif '$' in args:
        for i, a in enumerate(args):
            if a == '$':
                message = ' '.join(args[i + 1:])
                break
    if message:
        message += '\n'
    return message
