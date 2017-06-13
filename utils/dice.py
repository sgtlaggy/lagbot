import random
import re

ROLL = re.compile(r"^(?P<count>\d+)?d(?P<sides>\d+)((?P<high>\^(?P<highest>\d*))|(?P<low>v(?P<lowest>\d*)))?"
                  r"((?P<reroll>r|rr)(?P<rollunder>\d+))?(?P<explode>x)?(?P<ts>[ts])?$")


class Roll:
    def __init__(self, count, sides, highest=0, lowest=0, reroll=0, recursive=False,
                 explode=False, total=False, sort=False):
        self.count = count
        self.sides = sides
        if count < highest < 1:
            raise ValueError('Cannot give fewer than 1 or more values than dice rolled.')
        self.highest = highest
        if count < lowest < 1:
            raise ValueError('Cannot give fewer than 1 or more values than dice rolled.')
        self.lowest = lowest
        if sides <= reroll < 1:
            raise ValueError(f'Cannot reroll rolls lower than 1 or higher than {sides}')
        self.reroll = reroll
        self.recursive = recursive
        self.explode = explode
        self.total = total
        self.sort = sort

    def roll_one(self):
        r = random.randint(1, self.sides)
        if r == self.sides and self.explode:
            r = [r, random.randint(1, self.sides)]
        elif self.reroll:
            while r <= self.reroll:
                r = random.randint(1, self.sides)
                if not self.recursive:
                    break
        return r

    def roll(self):
        rolls = []
        for _ in range(self.count):
            r = self.roll_one()
            try:
                rolls.extend(r)
            except TypeError:
                rolls.append(r)
        if self.highest or self.lowest:
            if self.highest:
                s = sorted(rolls, reverse=True)
            else:
                s = sorted(rolls)
            end = s[:self.highest or self.lowest]
            r = []
            for roll in rolls:
                if roll in end:
                    end.remove(roll)
                    r.append(roll)
            rolls = r
        if self.total:
            return sum(rolls)
        if self.sort:
            return sorted(rolls)
        return rolls


def roll(arg):
    r = ROLL.match(arg)
    count = int(r.group('count') or 1)
    sides = int(r.group('sides'))
    highest = int(r.group('highest') or (1 if r.group('high') else 0))
    lowest = int(r.group('lowest') or (1 if r.group('low') else 0))
    reroll = int(r.group('rollunder') or 0)
    recursive = r.group('reroll') == 'rr'
    explode = bool(r.group('explode'))
    ts = r.group('ts')
    total = ts == 't'
    sort = ts == 's'
    return Roll(count, sides, highest, lowest, reroll, recursive, explode, total, sort).roll()
