import random
import typing

from discord.ext import commands
import discord

from .models import Fighter, FakeFighter, Game, EndReason, arena_id
from .modes import MODES, inject_help_modes
from .errors import SmashError
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
        self.delete_commands = (*short, self.end, self.repost, self.add, self.leave, self.rejoin)

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
    async def win(self, ctx, round_num: typing.Optional[int] = 0):
        """Mark a round as won by you."""
        player = ctx.player
        game = player.game
        round_num = round_num or (player.current_round + 1)
        if player.win(round_num - 1):
            if len(player.wins) == game.winning_score:
                await game.end(reason=EndReason.win)
            else:
                await game.update()

    @commands.command(aliases=['u'])
    @game_in_progress()
    async def undo(self, ctx, round_num: typing.Optional[int] = None, action='p'):
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

    @commands.command(aliases=['c'])
    @game_in_progress()
    async def change(self, ctx, attr, val: typing.Union[int, str]):
        """Change various aspects of your game.

        Available options:
        w, win, wins - Wins required to end the game. Will end immediately if someone is at or above the given value.
        m, mode, gamemode - Change the mode/ruleset.
        b, bans, maxbans - Change the allowed number of bans. If reduced, only the most recent bans will be kept.
        a, arena, id - Change the Arena ID listed. Omit value to remove the ID.
        """
        game = ctx.player.game
        if attr in {'w', 'win', 'wins'}:
            if isinstance(val, int):
                val = clamp(val, low=0)
                game.winning_score = val
                if val > 0 and any(len(p.wins) >= val for p in game.players.values()):
                    await game.end(reason=EndReason.win)
                    return
            else:
                raise SmashError(f'{val} is not a valid score.')
        elif attr in {'m', 'mode', 'gamemode'}:
            try:
                game.mode = MODES[val]
            except KeyError:
                raise SmashError(f'{val} is not a valid mode.')
        elif attr in {'b', 'bans', 'maxbans'}:
            if isinstance(val, int):
                val = clamp(val, low=0)
                game.max_bans = val
            else:
                raise SmashError(f'{val} is not a valid ban amount.')
        elif attr in {'a', 'arena', 'id'}:
            try:
                if val == '':
                    game.arena_id = None
                else:
                    game.arena_id = arena_id(val)
            except ValueError as e:
                raise SmashError(e)
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
        await game.update(destination=ctx)

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
        cmd = self.bot.get_command(ctx.view.get_word().lower())
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
