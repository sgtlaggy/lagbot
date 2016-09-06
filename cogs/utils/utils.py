class Not200(Exception):
    pass

class NotInDB(Exception):
    pass

def plural(num):
    return 's' if num != 1 else ''
