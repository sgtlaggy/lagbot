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


class ActionMenu(GameSelect):
    def __init__(self, *args, **kwargs):
        options = [discord.SelectOption(label='Win', value='win', emoji='\N{PARTY POPPER}'),
                   discord.SelectOption(label='Undo', value='undo', emoji='\N{LEFTWARDS ARROW WITH HOOK}\ufe0f'),
                   *[discord.SelectOption(label='Change Winning Score - {}'.format(n or '\N{INFINITY}'),
                                          value=f'change wins {n}', emoji='\N{CROWN}')
                     for n in (0, 3, 5, 10)],
                   *[discord.SelectOption(label=f'Change Ban Count - {n}',
                                          value=f'change bans {n}', emoji='\N{HAMMER}')
                     for n in (0, 1, 3)],
                   *[discord.SelectOption(label=f'Change Mode - {m.name}', value=f'change mode {m.name}',
                                          description=m.description, emoji='\N{NOTEBOOK WITH DECORATIVE COVER}')
                     for m in MODES.values()],
                   discord.SelectOption(label='Leave/Rejoin', value='active', emoji='\N{DOOR}'),
                   discord.SelectOption(label='Vote to End', value='end', emoji='\N{CHEQUERED FLAG}')]
        super().__init__(*args, placeholder='\N{PUSHPIN} Actions', options=options, **kwargs)

    async def _callback(self, interaction: discord.Interaction):
        ctx = FakeContext(self.view, interaction)
        parts = self.values[0].split()

        if parts[0] == 'active':
            if ctx.player.active:
                parts[0] = 'leave'
            else:
                parts[0] = 'rejoin'

        cmd = self.get_command(parts.pop(0))
        if parts:
            cmd = cmd.get_command(parts.pop(0))
            arg = parts.pop()
            if arg.isdigit():
                arg = int(arg)

            await cmd(ctx, arg)
        else:
            await cmd(ctx)



class GameView(ui.View):
    def __init__(self, game: Game, *args, **kwargs):
        self.game = game
        super().__init__(*args, **kwargs)

        for row, options in enumerate(FIGHTER_OPTIONS):
            self.add_item(PickFighterMenu(options=options, row=row))

        self.add_item(ActionMenu())

    def get_models(self, interaction: discord.Interaction):
        return self.game, self.game.players[interaction.user]

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user in self.game.players