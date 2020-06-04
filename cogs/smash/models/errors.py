from discord.ext import commands


class SmashError(commands.CommandError):
    def __init__(self, message=None, *args):
        if message is not None:
            super().__init__(str(message), *args)
        else:
            super().__init__(message, *args)
