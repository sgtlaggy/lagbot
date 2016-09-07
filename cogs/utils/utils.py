async def init_db(bot, table, *cols):
    async with bot.db.transaction():
        await bot.db.execute('''
            CREATE TABLE IF NOT EXISTS {} ({})
            '''.format(table, ', '.join(cols)))


class NotFound(Exception):
    pass


class NotInDB(Exception):
    pass


def plural(num):
    return 's' if num != 1 else ''
