import random
import typing

from discord.ext import commands
import discord

from .models import (Fighter, FakeFighter,
                     Game, EndReason, arena_id,
                     MODES, inject_help_modes,
                     SmashError,
                     FighterMenu, FighterPageSource,
                     GameView)
from utils import commaize, clamp


_NAME, *_ALIASES = MODES.keys()


def game_in_progress(*, player_active=True):
    async def pred(ctx):
        ctx.player = player = ctx.command.cog.players.get(ctx.author, None)
        return (player is not None
                and (player.active if player_active else not player.active)
                and player.game.channel == ctx.channel
                and ctx.message.content
                and not player.game._ending)
    return commands.check(pred)


class Smash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}  # {member: Player}
        self.short_commands = short = (self.pick, self.ban, self.unban, self.win, self.undo, self.change)
        self.delete_commands = (*short, *self.change.commands,
                                self.end, self.repost, self.add, self.leave, self.rejoin)

    @commands.command()
    async def fighters(self, ctx):
        """List all fighters in a neat menu."""
        users = None
        if ctx.author in self.players:
            users = self.players[ctx.author].game.players

        source = FighterPageSource(list(Fighter.all()), per_page=20)
        menu = FighterMenu(source)
        await menu.start(ctx)

    @commands.command(aliases=['p'])
    @game_in_progress()
    async def pick(self, ctx, round_num: typing.Optional[int] = None, *, fighter=''):
        """Pick a fighter to play in a given round."""
        player = ctx.player
        game = player.game
        if fighter in ('', 'rand', 'random'):
            fighter = random.choice([f for f in Fighter.all() if game.mode.pick_check(player, f)])
        elif fighter in FakeFighter.names:
            fighter = FakeFighter(fighter)
        else:
            fighter = Fighter.get_closest(fighter)
            allowed = game.mode.pick_check(player, fighter)
            if not allowed:
                raise SmashError(allowed)
        if round_num is not None:
            player.play(fighter, round_num - 1)
        else:
            player.play(fighter)
        await game.update()

    @commands.command(aliases=['b'])
    @game_in_progress()
    async def ban(self, ctx, *, fighter: Fighter):
        """Ban a fighter for everyone playing."""
        player = ctx.player
        game = player.game
        allowed = game.mode.ban_check(player, fighter)
        if not allowed:
            raise SmashError(allowed)
        player.ban(fighter)
        await game.update()

    @commands.command(aliases=['ub'])
    @game_in_progress()
    async def unban(self, ctx, *, fighter: Fighter):
        """Unban a fighter you have banned.

        Note: This is not necessary with a ban limit, as the oldest will automatically be removed when banning another."""
        player = ctx.player
        if player.has_banned(fighter):
            player.unban(fighter)
        else:
            raise SmashError(f'You have not banned {fighter}.')
        await player.game.update()

    @commands.command(aliases=['w'])
    @game_in_progress()
    async def win(self, ctx, round_num: int = 0):
        """Mark a round as won by you."""
        player = ctx.player
        game = player.game
        round_num = round_num or (player.current_round + 1)
        if player.win(round_num - 1):
            if player.wins == game.winning_score:
                await game.end(reason=EndReason.win)
            else:
                await game.update()

    @commands.command(aliases=['u'])
    @game_in_progress()
    async def undo(self, ctx, round_num: typing.Optional[int], action='p'):
        """Undo round actions such as playing or winning."""
        action = {'p': 'play', 'play': 'play', 'w': 'win', 'win': 'win'}.get(action, None)
        if action is None:
            return
        if round_num is None:
            undone = ctx.player.undo()
        else:
            undone = ctx.player.undo(action, round_num - 1)
        if undone:
            await ctx.player.game.update()

    @commands.group(aliases=['c'], invoke_without_command=True)
    @game_in_progress()
    async def change(self, ctx):
        """Change various aspects of your game."""
        await ctx.send_help(ctx.command)

    @change.command(aliases=['w', 'win'])
    @game_in_progress()
    async def wins(self, ctx, number: int):
        """Change number of wins required to end the game.

        If any player meets or exceeds the new value, the game will immediately end.
        """
        game = ctx.player.game
        number = clamp(number, low=0)
        game.winning_score = number
        if number > 0 and any(p.wins >= number for p in game.players.values()):
            await game.end(reason=EndReason.win)
        await game.update()

    @change.command(aliases=['m', 'gamemode'])
    @game_in_progress()
    async def mode(self, ctx, mode):
        """Change the gamemode.

        Previous rounds will count toward restrictions in the new mode.
        """
        game = ctx.player.game
        try:
            game.mode = MODES[mode.lower()]
        except KeyError:
            raise SmashError(f'{mode} is not a valid mode.')
        await game.update()

    @change.command(aliases=['b', 'maxbans'])
    @game_in_progress()
    async def bans(self, ctx, number: int):
        """Change the allowed number of bans.

        If someone has banned more than the new number of bans, only the most recent will be kept.
        """
        game = ctx.player.game
        number = clamp(number, low=0)
        game.max_bans = number
        await game.update()

    @change.command(aliases=['a', 'id'])
    @game_in_progress()
    async def arena(self, ctx, arena_id: typing.Optional[arena_id]):
        """Change, set, or remove the arena ID."""
        game = ctx.player.game
        game.arena_id = arena_id
        await game.update()

    @commands.command()
    @game_in_progress()
    async def repost(self, ctx, channel: discord.TextChannel = None):
        """Repost the game embed to this, or another, channel."""
        await ctx.player.game.update(destination=channel or ctx)

    @commands.command()
    @game_in_progress()
    async def end(self, ctx):
        """Vote to end the game. Requires majority vote to succeed."""
        game = ctx.player.game
        ctx.player.vote_to_end()
        if sum(p.end for p in game.players.values() if p.active) >= game.votes_to_end:
            await game.end(reason=EndReason.vote)
        else:
            await game.update()

    @commands.command(name=_NAME, aliases=_ALIASES)
    @inject_help_modes
    async def _smash(self, ctx,
                     arena_id: typing.Optional[arena_id],
                     winning_score: typing.Optional[int],
                     players: commands.Greedy[discord.Member],
                     max_bans: typing.Optional[int] = None):
        """Start a smash match.

        {modes}

        Available commands while match is in progress:
        w            "win" | mark the latest round as a win
        w 2                | mark round 2 as a win
        p name      "pick" | pick a fighter
        p 2 name           | pick a fighter and insert at round 2
        p -                | pick nothing (skip round)
        p ???              | pick unknown character (if character is not yet added to bot)
        p rand/random      | pick a random fighter
        p                  | pick a random fighter
        u           "undo" | undo your most recent action (win/pick)
        u 2                | undo round 2, removing fighter + win
        u 2 w              | undo round 2's win, leaving the fighter
        b name       "ban" | ban a fighter
        ub name    "unban" | unban a fighter
        c w 3     "change" | change winning score to 3
        c m elimination    | change gamemode to elimination
        c b 2              | change allowed number of bans to 2
        c a ABC12          | change arena id to ABC12
        c a                | remove arena id
        ,repost #channel   | repost the board to another channel
        ,repost            | repost the board
        ,end               | vote to end the match. requires majority
        ,add @User @User2  | add users to the game. this will also insert blank rounds for them.
        ,leave             | leave the game
        ,rejoin            | rejoin a game after leaving
        """
        if ctx.author not in players:
            players = (ctx.author, *players)
        count = len(players)
        if count == 1:
            await ctx.send('Not enough players to start a game.')
            return
        elif count > 25:
            await ctx.send('Too many players to start a game. Limit of 25 players.')
            return
        if winning_score is None:
            winning_score = 0
        else:
            winning_score = clamp(winning_score, low=0)
        already_in_game = [p for p in players if p in self.players]
        if already_in_game:
            if len(already_in_game) == 1:
                await ctx.send(f'{already_in_game[0].mention} is already in a game.', delete_after=5)
            else:
                await ctx.send(f'{commaize(m.mention for m in already_in_game)} are already in a game.', delete_after=5)
            return
        mode = MODES[ctx.invoked_with]
        game = Game(ctx, arena_id, mode, players, winning_score, max_bans, ctx.message.created_at)
        self.players.update(game.players)
        await game.update(destination=ctx, view=GameView(game))

    @commands.command()
    @game_in_progress()
    async def add(self, ctx, *new_players: discord.Member):
        """Add users to your game.

        Note: This will add blank rounds for them to join you on your current round."""
        player = ctx.player
        game = player.game
        already_in_game, to_add = [], []
        for m in new_players:
            if m not in self.players:
                to_add.append(m)
            elif m not in game.players:
                already_in_game.append(m)
            else:
                game.players[m].active = True
        if already_in_game:
            if len(already_in_game) == 1:
                await ctx.send(f'{already_in_game[0].mention} is already in a game.', delete_after=5)
            else:
                await ctx.send(f'{commaize(m.mention for m in already_in_game)} are already in a game.', delete_after=5)
        if not to_add:
            return
        players = game.add_players(*to_add)
        self.players.update(players)
        round_num = player.current_round - 1
        if round_num >= 0:
            for p in players.values():
                p.play(FakeFighter('-'), round_num)
        await game.update()

    @commands.command()
    @game_in_progress()
    async def leave(self, ctx):
        """Leave your current game.

        Note: This does not free you up to join another game.
        You may rejoin with the `rejoin` command."""
        ctx.player.active = False
        await ctx.player.game.update()

    @commands.command()
    @game_in_progress(player_active=False)
    async def rejoin(self, ctx):
        """Rejoin your game."""
        ctx.player.active = True
        await ctx.player.game.update()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if not msg.content:
            return
        ctx = await self.bot.get_context(msg)
        if ctx.valid:
            return
        cmd = self.bot.get_command(ctx.view.get_word().lower())
        prefix = await self.bot.get_prefix(msg)
        if isinstance(prefix, list):
            ctx.prefix = prefix[-1]
        else:
            ctx.prefix = prefix
        if cmd is None or cmd.cog is not self or cmd not in self.short_commands:
            return
        try:
            await cmd.invoke(ctx)
        except commands.CommandInvokeError as e:
            self.bot.dispatch('command_error', ctx, e)
            await msg.channel.send(e.original, delete_after=5)
        except (commands.ConversionError, commands.UserInputError, SmashError) as e:
            e = getattr(e, 'original', e)
            await msg.channel.send(e, delete_after=5)
        except commands.CommandError:  # don't care about check error/command not found
            pass
        except Exception as e:
            self.bot.dispatch('command_error', ctx, commands.CommandInvokeError(e))

    async def cog_check(self, ctx):
        return ctx.guild

    async def cog_before_invoke(self, ctx):
        if ctx.command in self.delete_commands:
            await ctx.message.delete(delay=1)
