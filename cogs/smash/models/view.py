import functools
import random

from discord import ui
import discord


from .game import Game, EndReason
from .fighter import Fighter, FakeFighter
from .modes import MODES


FIGHTER_OPTIONS = [discord.SelectOption(label=fighter.name, emoji=fighter.emoji) for fighter in Fighter.all()]
FIGHTER_OPTIONS = list(discord.utils.as_chunks(FIGHTER_OPTIONS, 22))
PLACEHOLDERS = [str(group[0]) for group in FIGHTER_OPTIONS]
RANDOM_FIGHTER = discord.SelectOption(label='random', emoji='\N{GAME DIE}')
UNPLAYED_ROUND = discord.SelectOption(label='sit out', emoji='\N{CHAIR}')


class GameView(ui.View):
    def __init__(self, game: Game, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        
    def get_models(self, interaction: discord.Interaction):
        return self.game, self.game.players[interaction.user]
        
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user in self.game.players
    
    async def pick_fighter(self, select: ui.Select, interaction: discord.Interaction):
        game, player = self.get_models(interaction)
        value = select.values[0]
        
        if value == UNPLAYED_ROUND.value:
            fighter = FakeFighter('-')
        else:
            fighter = Fighter.get_exact(value)

        allowed = self.game.mode.pick_check(player, fighter)
        if allowed:
            self.game.players[interaction.user].play(fighter)
            await game.update()
        else:
            await interaction.response.send_message(allowed, ephemeral=True)
    
    @ui.select(placeholder=PLACEHOLDERS[0], options=FIGHTER_OPTIONS[0])
    async def pick_1(self, select, interaction):
        await self.pick_fighter(select, interaction)
    
    @ui.select(placeholder=PLACEHOLDERS[1], options=FIGHTER_OPTIONS[1])
    async def pick_2(self, select, interaction):
        await self.pick_fighter(select, interaction)
    
    @ui.select(placeholder=PLACEHOLDERS[2], options=FIGHTER_OPTIONS[2])
    async def pick_3(self, select, interaction):
        await self.pick_fighter(select, interaction)
    
    @ui.select(placeholder=PLACEHOLDERS[3], options=FIGHTER_OPTIONS[3] + [RANDOM_FIGHTER, UNPLAYED_ROUND])
    async def pick_4(self, select, interaction):
        await self.pick_fighter(select, interaction)
            
    @ui.button(label='Win', emoji='\N{PARTY POPPER}', style=discord.ButtonStyle.success)
    async def win_latest_round(self, button: ui.Button, interaction: discord.Interaction):
        game, player = self.get_models(interaction)
        if player.win(player.current_round):
            if player.wins == game.winning_score:
                await game.end(reason=EndReason.win)
            else:
                await game.update()

    @ui.button(label='Undo', emoji='\N{LEFTWARDS ARROW WITH HOOK}\ufe0f', style=discord.ButtonStyle.primary)
    async def undo_latest_action(self, button: ui.Button, interaction: discord.Interaction):
        game, player = self.get_models(interaction)
        if player.undo():
            await game.update()