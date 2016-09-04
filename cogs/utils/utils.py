class Not200(Exception):
    pass

def plural(num):
    return 's' if num != 1 else ''
