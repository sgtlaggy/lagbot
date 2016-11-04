import sys
import os

from lagbot import LagBot

# Files and Paths
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
config_file = os.path.join(app_path, 'config.json')

# Discord Client/Bot
command_prefix = '!'
help_attrs = {'hidden': True}
initial_cogs = ['cogs.{}'.format(cog) for cog in [
    'cog', 'management', 'misc', 'meta', 'rdanny', 'overwatch']]

if __name__ == '__main__':
    bot = LagBot(command_prefix=command_prefix,
                 help_attrs=help_attrs,
                 config_file=config_file,
                 debug=any('debug' in arg.lower() for arg in sys.argv))

    for cog in initial_cogs:
        try:
            bot.load_extension(cog)
        except Exception as e:
            print("Couldn't load cog {}\n{}: {}".format(
                cog, type(e).__name__, e))

    try:
        bot.run()
    except Exception as e:
        print("""
        ******************************
        ***BOT CRASHED OR SOMETHING***
        ******************************""")
        print(e)
