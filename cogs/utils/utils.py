class NotFound(Exception):
    pass


class NotInDB(Exception):
    pass


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
