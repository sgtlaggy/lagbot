from discord.ext import commands


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self._bot = bot

    @property
    def bot(self):
        return self._bot
