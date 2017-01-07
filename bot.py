import functools
import asyncio
import logging
import signal
import sys
import os

from lagbot import LagBot

# stolen from R.Danny
try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

debug = any('debug' in arg.lower() for arg in sys.argv)
logging.basicConfig(level=logging.INFO if debug else logging.WARNING)

# Files and Paths
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
config_file = os.path.join(app_path, 'config.json')

# Discord Client/Bot
command_prefix = '!'
help_attrs = {'hidden': True}
initial_cogs = [f'cogs.{cog}' for cog in [
    'cog', 'images', 'management', 'meta',
    'misc', 'overwatch', 'rdanny', 'tags']]

if __name__ == '__main__':
    bot = LagBot(command_prefix=command_prefix, help_attrs=help_attrs,
                 config_file=config_file, debug=debug)

    bot.loop.add_signal_handler(
        signal.SIGTERM,
        functools.partial(bot.loop.create_task, bot.logout()))

    for cog in initial_cogs:
        try:
            bot.load_extension(cog)
        except Exception as e:
            logging.exception(f"Couldn't load cog {cog}")

    bot.run()
    status = getattr(bot, 'exit_status', 0)
    if status:
        logging.critical(f'Exiting with {status}.')
    logging.shutdown()
    sys.exit(status)
