import traceback
import random
import typing

from discord.ext import commands
import discord

from .models import Fighter, FakeFighter, Game
from .errors import SmashError
from .modes import MODES, inject_help_modes
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

    async def end_game(self, game, early=False):
        game._ending = True
        await game.update()
        mentions = [m.mention for m in game.players]
        if early:
            await game.send(f'{" ".join(mentions)}\nThe game ended by majority vote.', delete_after=15)
        else:
            member, player = max(game.players.items(), key=lambda p: len(p[1].wins))
            await game.send(f'{" ".join(mentions)}\n**{member.display_name} won!**', delete_after=15)
        for m in game.players:
            self.players.pop(m, None)

    @commands.command(aliases=['p'])
    @game_in_progress()
    async def pick(self, ctx, round_num: typing.Optional[int] = None, *, fighter=''):
        player = ctx.player
        game = player.game
        if fighter in ('', 'rand', 'random'):
            fighter = random.choice([f for f in Fighter.all() if game.mode.pick_check(player, f)])
        elif fighter in FakeFighter.ALLOWED:
            fighter = FakeFighter(fighter)
        else:
            fighter = Fighter.get_closest(fighter)
            if not game.mode.pick_check(player, fighter):
                raise SmashError(f'{fighter} cannot be picked.')
        if round_num is not None:
            player.play(fighter, round_num - 1)
        else:
            player.play(fighter)
        await game.update()

    @commands.command(aliases=['b'])
    @game_in_progress()
    async def ban(self, ctx, *, fighter: Fighter):
        player = ctx.player
        game = player.game
        if game.mode.ban_check(player, fighter):
            player.ban(fighter)
        else:
            raise SmashError(f'{fighter} cannot be banned.')
        await game.update()

    @commands.command(aliases=['ub'])
    @game_in_progress()
    async def unban(self, ctx, *, fighter: Fighter):
        player = ctx.player
        if player.has_banned(fighter):
            player.unban(fighter)
        else:
            raise SmashError(f'You have not banned {fighter}.')
        await player.game.update()

    @commands.command(aliases=['w'])
    @game_in_progress()
    async def win(self, ctx, round_num: typing.Optional[int] = 0):
        player = ctx.player
        game = player.game
        round_num = round_num or (player.current_round + 1)
        if player.win(round_num - 1):
            if len(player.wins) == game.winning_score:
                await self.end_game(game)
            else:
                await game.update()

    @commands.command(aliases=['u'])
    @game_in_progress()
    async def undo(self, ctx, round_num: typing.Optional[int] = None, action='p'):
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
        game = ctx.player.game
        if attr in {'w', 'win'}:
            if isinstance(val, int):
                val = clamp(val, low=0)
                game.winning_score = val
                if val > 0 and any(len(p.wins) >= val for p in game.players.values()):
                    await self.end_game(game)
                else:
                    await game.update()
            else:
                raise SmashError(f'{val} is not a valid score.')
        elif attr in {'m', 'mode', 'gamemode'}:
            try:
                game.mode = MODES[val]
            except KeyError:
                raise SmashError(f'{val} is not a valid mode.')
            else:
                await game.update()
        elif attr in {'b', 'bans', 'maxbans'}:
            if isinstance(val, int):
                val = clamp(val, low=0)
                game.max_bans = val
                await game.update()
            else:
                raise SmashError(f'{val} is not a valid ban amount.')

    @commands.command()
    @game_in_progress()
    async def repost(self, ctx, channel: discord.TextChannel = None):
        await ctx.player.game.update(repost_to=channel or ctx)

    @commands.command()
    @game_in_progress()
    async def end(self, ctx):
        game = ctx.player.game
        ctx.player.vote_to_end()
        await game.update()
        if sum(p.end for p in game.players.values() if p.active) >= game.votes_to_end:
            await self.end_game(game, early=True)

    @commands.command(name=_NAME, aliases=_ALIASES)
    @inject_help_modes
    async def _smash(self, ctx, winning_score: int,
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
        ,repost #channel   | repost the board to another channel
        ,repost            | repost the board
        ,end               | vote to end the match. requires majority
        ,add @User @User2  | add users to the game. this will also insert blank rounds for them.
        ,leave             | leave the game
        ,rejoin            | rejoin a game after leaving
        """
        if ctx.author not in players:
            players = (ctx.author, *players)
        if len(players) == 1:
            return
        winning_score = clamp(winning_score, low=0)
        already_in_game = [p for p in players if p in self.players]
        if already_in_game:
            if len(already_in_game) == 1:
                await ctx.send(f'{already_in_game[0].mention} is already in a game.', delete_after=5)
            else:
                await ctx.send(f'{commaize(m.mention for m in already_in_game)} are already in a game.', delete_after=5)
            return
        mode = MODES[ctx.invoked_with]
        game = Game(ctx, mode, players, winning_score, max_bans, ctx.message.created_at)
        self.players.update(game.players)
        game.message = await ctx.send(embed=game.embed)

    @commands.command()
    @game_in_progress()
    async def add(self, ctx, *new_players: discord.Member):
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
        ctx.player.active = False
        await ctx.player.game.update()

    @commands.command()
    @game_in_progress(player_active=False)
    async def rejoin(self, ctx):
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
        except (commands.ConversionError, commands.CommandInvokeError) as e:
            await msg.channel.send(e.original, delete_after=5)
        except (commands.UserInputError, SmashError) as e:
            await msg.channel.send(e, delete_after=5)
        except commands.CommandError:  # don't care about check error/command not found
            pass
        except Exception:
            print(traceback.format_exc(), flush=True)

    async def cog_check(self, ctx):
        return ctx.guild

    async def cog_before_invoke(self, ctx):
        if ctx.command in self.delete_commands:
            await ctx.message.delete(delay=1)
