from dataclasses import dataclass
from collections import deque

from .fighter import Fighter, FakeFighter


@dataclass
class Round:
    fighter: Fighter
    win: bool = False

    def __str__(self):
        return '{1}{0}{1}'.format(self.fighter, '__' if self.win else '')


class Player:
    def __init__(self, member, game):
        self.member = member
        self.game = game
        self.rounds = []
        self.bans = deque()
        self.end = False
        self.active = True

    @property
    def current_round(self):
        return len(self.rounds) - 1

    @property
    def wins(self):
        return sum(r.win for r in self.rounds)

    @property
    def latest_win_round(self):
        for ind, round_ in enumerate(reversed(self.rounds), 1):
            if round_.win:
                return len(self.rounds) - ind
        return -1

    def has_played(self, fighter):
        if isinstance(fighter, FakeFighter):
            return False
        for round_ in self.rounds:
            if round_.fighter == fighter:
                return True
        return False

    def has_banned(self, fighter):
        return fighter in self.bans

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
                self.rounds.extend(Round(FakeFighter('-')) for _ in range(round_diff))
            if self.rounds[round_num].fighter.replace_on_insert:
                self.rounds[round_num].fighter = fighter
            else:
                self.rounds.insert(round_num, Round(fighter))
        else:
            self.rounds.append(Round(fighter))

    def win(self, round_num=None):
        if round_num is None:
            round_num = self.current_round
        try:
            round_ = self.rounds[round_num]
        except IndexError:
            return False
        else:
            if round_.win:
                return False
            round_.win = True
            return True

    def undo(self, remove_action=None, round_num=None):
        if not self.rounds:
            return False
        if round_num is None:
            round_num = -1
            round_ = self.rounds[round_num]
            if remove_action is None and not round_.win:
                remove_action = 'play'
        else:
            try:
                round_ = self.rounds[round_num]
            except IndexError:
                return False
        if remove_action == 'play':
            self.rounds.pop(round_num)
        else:
            round_.win = False
        return True
