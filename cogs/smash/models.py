from functools import lru_cache
from collections import deque
import abc
import re

from discord.ext import commands
import discord

from .data import fighters as _fighters
from .errors import SmashError

WORD = re.compile(r'\W+')


def find_ngrams(text: str, number: int = 3) -> set:
    """https://stackoverflow.com/a/52389482
    returns a set of ngrams for the given string
    :param text: the string to find ngrams for
    :param number: the length the ngrams should be. defaults to 3 (trigrams)
    :return: set of ngram strings
    """
    if not text:
        return set()
    words = [f'  {x} ' for x in WORD.split(text.lower()) if x.strip()]
    ngrams = set()
    for word in words:
        for x in range(0, len(word) - number + 1):
            ngrams.add(word[x:x + number])
    return ngrams


def compare_ngrams(ngrams1, ngrams2):
    """https://stackoverflow.com/a/52389482
    Finds the similarity between 2 ngrams.
    0 being completely different, and 1 being equal
    """
    unique = len(ngrams1 | ngrams2)
    equal = len(ngrams1 & ngrams2)
    return float(equal) / float(unique)


class Player:
    def __init__(self, member, game):
        self.member = member
        self.game = game
        self.fighters = []
        self.wins = []
        self.bans = deque()
        self.end = False
        self.active = True

    def has_played(self, fighter):
        return fighter in self.fighters and not isinstance(fighter, FakeFighter)

    def has_banned(self, fighter):
        return fighter in self.bans

    @property
    def current_round(self):
        return len(self.fighters) - 1

    def ban(self, fighter):
        self.bans.append(fighter)

    def unban(self, fighter):
        self.bans.remove(fighter)

    def vote_to_end(self):
        self.end = not self.end

    def play(self, fighter, round_num=None):
        if round_num is not None:
            round_diff = round_num - self.current_round
            if round_diff > 0:
                self.fighters.extend([FakeFighter('-')] * round_diff)
            if isinstance(self.fighters[round_num], FakeFighter):
                self.fighters[round_num] = fighter
            else:
                self.fighters.insert(round_num, fighter)
                for i, rnum in enumerate(self.wins):
                    if rnum >= round_num:
                        self.wins[i] += 1
        else:
            self.fighters.append(fighter)

    def win(self, round_num=None):
        if round_num is None:
            round_num = self.current_round
        if not self.fighters or self.fighters[round_num] is None or round_num in self.wins:
            return False
        self.wins.append(round_num)
        return True

    def undo(self, remove_action=None, round_num=None):
        if not self.fighters:
            return False
        if round_num is None:
            round_num = self.current_round
            if remove_action is None and round_num not in self.wins:
                remove_action = 'play'
        removed = False
        if remove_action == 'play':
            self.fighters.pop(round_num)
            removed = True
        if round_num in self.wins:
            self.wins.remove(round_num)
        if removed:
            for i, rnum in enumerate(self.wins):
                if rnum >= round_num:
                    self.wins[i] -= 1
        return True


class Game:
    def __init__(self, ctx, mode, members, winning_score, max_bans, created_at):
        self.ctx = ctx
        self.players = {}
        self.add_players(*members)
        self.mode = mode
        self.winning_score = winning_score
        self.max_bans = max_bans
        self.created_at = created_at
        self.message = None
        self._ending = False

    @property
    def channel(self):
        try:
            return self.message.channel
        except AttributeError:
            return None

    @property
    def send(self):
        return self.message.channel.send

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
        e.title = self.mode.name
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
            win_count = len(player.wins)
            try:
                latest_win = max(player.wins)
            except ValueError:
                latest_win = -1
            if latest_win > last_round:
                last_fighter = player.fighters[latest_win]
                last_round = latest_win
            if self._ending:
                win_emoji = '\\\N{TROPHY}' if win_count >= self.winning_score else ''
                end_emoji = ''
            else:
                win_emoji = ''
                end_emoji = '\\\N{CROSS MARK}' if player.end else ''
            name = '{active}**{name}**{active}\n{winning}{end}Wins: {wins}'.format(
                name=member.name, wins=win_count,
                winning=win_emoji, end=end_emoji,
                active='' if player.active else '~~')
            fighters = []
            for ind, fighter in enumerate(player.fighters):
                fighters.append('{0}. {2}{1}{2}'.format(ind + 1, fighter, '__' if ind in player.wins else ''))
            e.add_field(name=name, value='\n'.join(fighters) or '\u200b')
        e.set_footer(text=f'First to {self.winning_score} wins! | Started')
        e.timestamp = self.created_at
        if last_round > -1:
            e.color = last_fighter.color
        return e

    async def update(self, *, embed=None, repost_to=None):
        embed = embed or self.embed
        if repost_to:
            old_msg = self.message
            try:
                self.message = await repost_to.send(embed=embed)
            except Exception as e:
                await self.send(e, delete_after=5)
            else:
                await old_msg.delete()
        else:
            await self.message.edit(embed=embed)

    def add_players(self, *members):
        players = {member: Player(member, self) for member in members}
        self.players.update(players)
        return players

    def is_banned(self, fighter):
        return any(p.has_banned(fighter) for p in self.players.values())


class Fighter(commands.Converter):
    __fighters = {}

    async def convert(self, ctx, arg):
        return self.get_closest(arg)

    @classmethod
    def add(cls, name, color):
        self = cls()
        self.name = name
        self.color = color
        self.__ngrams = find_ngrams(name)
        cls.__fighters[name] = self

    @classmethod
    def all(cls):
        return list(cls.__fighters.values())

    @classmethod
    def get(cls, name):
        try:
            return cls.__fighters.get(name)
        except KeyError:
            raise SmashError(f'{name} is not a valid fighter.')

    @classmethod
    @lru_cache()
    def get_closest(cls, name):
        ngrams = find_ngrams(name)
        similarities = {fighter: compare_ngrams(fighter.__ngrams, ngrams) for fighter in cls.__fighters.values()}
        most_similar = max(similarities.items(), key=lambda p: p[1])
        if most_similar[1] == 0:
            raise SmashError(f'{name} is not a valid fighter.')
        return most_similar[0]

    def __str__(self):
        return self.name


class _FakeFighter(abc.ABC):
    ALLOWED = ('-', '???')
    __instances = {}  # hack to only ever have 1 + len(ALLOWED) instances

    @classmethod
    def populate(cls):
        for val in cls.ALLOWED:
            self = cls()
            self.name = val
            self.color = 0xfffffe
            cls.__instances[val] = self

    def __call__(self, val):
        if val not in self.ALLOWED:
            raise ValueError(f'Argument must be one of {self.ALLOWED}')
        return self.__instances[val]

    def __instancecheck__(self, instance):
        return isinstance(instance, self.__class__)

    def __str__(self):
        return self.name


FakeFighter = _FakeFighter()
FakeFighter.populate()


for fighter_data in _fighters:
    Fighter.add(*fighter_data)
