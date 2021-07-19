from typing import Union
import functools
import random

from discord.ext import commands
from discord import ui
import discord


from .game import Game, EndReason
from .fighter import Fighter, FakeFighter
from .modes import MODES
from .errors import SmashError


FIGHTER_OPTIONS = [discord.SelectOption(label=fighter.name, emoji=fighter.emoji) for fighter in Fighter.all()]
FIGHTER_OPTIONS = list(discord.utils.as_chunks(FIGHTER_OPTIONS, 22))
RANDOM_FIGHTER = discord.SelectOption(label='random', emoji='\N{GAME DIE}')
UNPLAYED_ROUND = discord.SelectOption(label='sit out', value='-', emoji='\N{CHAIR}')
FIGHTER_OPTIONS[-1] += [RANDOM_FIGHTER, UNPLAYED_ROUND]


class FakeContext:
    def __init__(self, view: ui.View, interaction: discord.Interaction):
        self.author = interaction.user
        self.channel = self

        self.interaction = interaction
        _, self.player = view.get_models(interaction)

    async def send(self, *args, delete_after=None, **kwargs):
        return await self.interaction.response.send_message(*args, **kwargs, ephemeral=True)


class GameSelect(ui.Select):
    def get_command(self, command: str) -> Union[commands.Command, commands.Group]:
        return self.view.game.context.bot.get_command(command)

    async def callback(self, interaction: discord.Interaction):
        try:
            await self._callback(interaction)
        except SmashError as err:
            await interaction.response.send_message(str(err), ephemeral=True)


class PickFighterMenu(GameSelect):
    def __init__(self, *args, options: list[discord.SelectOption], **kwargs):
        super().__init__(*args, placeholder=str(options[0]), options=options, **kwargs)

    async def _callback(self, interaction: discord.Interaction):
        ctx = FakeContext(self.view, interaction)
        cmd = self.get_command('pick')
        await cmd(ctx, fighter=self.values[0])


class GameView(ui.View):
    def __init__(self, game: Game, *args, **kwargs):
        self.game = game
        super().__init__(*args, **kwargs)
        for row, options in enumerate(FIGHTER_OPTIONS):
            self.add_item(PickFighterMenu(options=options, row=row))

    def get_models(self, interaction: discord.Interaction):
        return self.game, self.game.players[interaction.user]

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user in self.game.players

    @ui.button(label='Win', emoji='\N{PARTY POPPER}', style=discord.ButtonStyle.success, row=4)
    async def win_latest_round(self, button: ui.Button, interaction: discord.Interaction):
        game, player = self.get_models(interaction)
        if player.win(player.current_round):
            if player.wins == game.winning_score:
                await game.end(reason=EndReason.win)
            else:
                await game.update()

    @ui.button(label='Undo', emoji='\N{LEFTWARDS ARROW WITH HOOK}\ufe0f', style=discord.ButtonStyle.primary, row=4)
    async def undo_latest_action(self, button: ui.Button, interaction: discord.Interaction):
        game, player = self.get_models(interaction)
        if player.undo():
            await game.update()