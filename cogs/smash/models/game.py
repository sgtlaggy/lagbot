from collections import deque
from enum import Enum
import asyncio
import re

import discord

from .player import Player


ARENA_ID = re.compile(r'^[0-9A-HJ-NP-Y]{5}$', flags=re.IGNORECASE)


def arena_id(arg):
    if ARENA_ID.match(arg):
        return arg.upper()
    raise ValueError(f'{arg} is not a valid Arena ID.')


class EndReason(Enum):
    win = 0
    vote = 1
    inactivity = 2


class Game:
    def __init__(self, ctx, arena_id, mode, members, winning_score, max_bans, created_at):
        self.context = ctx
        self.loop = ctx.bot.loop
        self.arena_id = arena_id
        self.players = {}
        self.add_players(*members)
        self.mode = mode
        self.winning_score = winning_score
        self.max_bans = max_bans
        self.created_at = created_at
        self.message = None
        self._ending = False
        self.__hide_rounds = 0
        self._timer = None

    def restart_timer(self):
        if self._timer:
            self._timer.cancel()
        self._timer = self.loop.create_task(self.__inactivity_timer())

    async def __inactivity_timer(self):
        await asyncio.sleep(60 * 10)

        confirmation = await self.send('Are you still playing?')
        emojis = ('\N{WHITE HEAVY CHECK MARK}', '\N{CROSS MARK}')
        for emoji in emojis:
            await confirmation.add_reaction(emoji)
        votes = set()

        def check(reaction, user):
            if not (user in self.players and reaction.message.id == confirmation.id):
                return False
            elif reaction.emoji == emojis[0]:
                return True
            elif reaction.emoji == emojis[1] and user not in votes:
                votes.add(user)
                return len(votes) == self.votes_to_end

        try:
            reaction, user = await self.context.bot.wait_for('reaction_add', check=check, timeout=60)
        except asyncio.TimeoutError:
            await self.end(reason=EndReason.inactivity)
        else:
            if reaction.emoji == emojis[1]:
                await self.end(reason=EndReason.vote)
        finally:
            await confirmation.delete()
            if not self._ending:
                self.restart_timer()

    @property
    def channel(self):
        try:
            return self.message.channel
        except AttributeError:
            return None

    @property
    def send(self):
        return self.channel.send

    @property
    def max_bans(self):
        return self.__max_bans

    @max_bans.setter
    def max_bans(self, maxlen):
        self.__max_bans = maxlen
        for player in self.players.values():
            player.bans = deque(player.bans, maxlen)

    @property
    def votes_to_end(self):
        return sum(1 for p in self.players.values() if p.active) // 2 + 1

    @property
    def embed(self):
        e = discord.Embed()
        title = self.mode.name
        if self.arena_id:
            title = f'{title} - {self.arena_id}'
        e.title = title
        desc = [self.mode.description]
        if self.max_bans:
            desc.append(f'Max bans: {self.max_bans}')
        bans = []
        for m, p in self.players.items():
            if p.bans:
                bans.append(f'**{m.display_name}**: {", ".join(f.name for f in p.bans)}')
        if bans:
            desc.append('**Bans:**')
            desc.extend(bans)
        e.description = '\n'.join(desc)
        last_fighter, last_round = None, -1
        for index, pair in enumerate(self.players.items()):
            member, player = pair
            win_count = player.wins
            try:
                latest_win = player.latest_win_round
            except ValueError:
                latest_win = -1
            if latest_win > last_round:
                last_fighter = player.rounds[latest_win].fighter
                last_round = latest_win
            if self._ending and win_count >= self.winning_score:
                status = '\\\N{TROPHY}'
            elif player.end:
                status = '\\\N{CROSS MARK}'
            else:
                status = ''
            name = '{active}**{name}**{active}\n{status}Wins: {wins}'.format(
                name=member.name, wins=win_count, status=status,
                active='' if player.active else '~~')
            rounds = []
            for ind, round_ in enumerate(player.rounds[self.__hide_rounds:], self.__hide_rounds):
                rounds.append(f'{ind + 1}. {round_}')
            e.add_field(name=name, value='\n'.join(rounds) or '\u200b')
        if self.winning_score:
            e.set_footer(text=f'First to {self.winning_score} wins! | Started')
        else:
            e.set_footer(text='Started')
        e.timestamp = self.created_at
        if last_round > -1:
            e.color = last_fighter.color
        if len(e) > 5000:
            self.__hide_rounds += 1
        return e

    async def update(self, *, embed=None, destination=None):
        embed = embed or self.embed
        if destination:
            old_msg = self.message
            try:
                self.message = await destination.send(embed=embed)
            except Exception as e:
                await self.send(e, delete_after=5)
            else:
                if old_msg:
                    await old_msg.delete()
        else:
            await self.message.edit(embed=embed)
        self.restart_timer()

    def add_players(self, *members):
        players = {member: Player(member, self) for member in members}
        self.players.update(players)
        return players

    def is_banned(self, fighter):
        return any(p.has_banned(fighter) for p in self.players.values())

    async def end(self, reason=EndReason.win):
        self._ending = True
        if self._timer:
            self._timer.cancel()
        await self.update()
        mentions = ' '.join([m.mention for m in self.players])
        if reason is EndReason.vote:
            await self.send(f'{mentions}\nThe game ended by majority vote.', delete_after=15)
        elif reason is EndReason.inactivity:
            await self.send(f'{mentions}\nThe game ended due to inactivity.', delete_after=15)
        else:
            member, player = max(self.players.items(), key=lambda p: p[1].wins)
            await self.send(f'{mentions}\n**{member.display_name} won!**', delete_after=15)
        for m in self.players:
            self.context.cog.players.pop(m, None)
