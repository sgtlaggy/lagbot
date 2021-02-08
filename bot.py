#!/usr/bin/env python3
import logging
import sys

from discord.ext import commands

from lagbot import LagBot

# stolen from R.Danny
try:
    import uvloop
except ImportError:
    pass
else:
    uvloop.install()

logging.basicConfig(level=logging.WARNING)

initial_cogs = ['cogs.meta', 'cogs.smash']

if __name__ == '__main__':
    bot = LagBot()

    for cog in initial_cogs:
        try:
            bot.load_extension(cog)
        except commands.ExtensionError:
            logging.exception(f"Couldn't load cog {cog}")

    status = bot.run()
    logging.critical(f'Exiting with {status}.')
    logging.shutdown()
    sys.exit(status)
