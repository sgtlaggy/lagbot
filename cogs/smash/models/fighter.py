from functools import lru_cache
import re

from discord.ext import commands

from ..data import fighters as _fighters
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
    ~~0 being completely different, and 1 being equal~~

    Keeping above reference, though it has been modified.
    Instead of 0-1, this function returns the number of similar ngrams.
    """
    return len(ngrams1 & ngrams2)


class Fighter(commands.Converter):
    __fighters = {}

    async def convert(self, ctx, arg):
        return self.get_closest(arg)

    @classmethod
    def add(cls, name, color, aliases=()):
        self = cls()
        self.name = name
        self.color = color
        self.aliases = aliases
        self.replace_on_insert = False
        self.__ngrams = frozenset(find_ngrams(name).union(*(find_ngrams(alias) for alias in aliases)))
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
        sorted_sims = sorted(similarities.items(), key=lambda pair: (pair[1], len(pair[0].name)))
        highest = max(pair[1] for pair in sorted_sims)
        if highest == 0:
            raise SmashError(f'{name} is not a valid fighter.')

        filtered = filter(lambda pair: pair[1] == highest, sorted_sims)
        most_similar = next(filtered)
        return most_similar[0]

    def __str__(self):
        return self.name


class _FakeFighter:
    ALLOWED = {'-': True, '???': False}
    __instances = {}  # hack to only ever have 1 + len(ALLOWED) instances

    @classmethod
    def populate(cls):
        for val, replace in cls.ALLOWED.items():
            self = cls()
            self.name = val
            self.color = 0xfffffe
            self.replace_on_insert = replace
            cls.__instances[val] = self

    @property
    def names(self):
        return self.__instances.keys()

    def __instancecheck__(self, instance):  # allows instance to act as class in `isinstance`
        return isinstance(instance, self.__class__)

    def __call__(self, val):
        if val not in self.ALLOWED:
            raise ValueError(f'Argument must be one of ({", ".join(self.ALLOWED)})')
        return self.__instances[val]

    def __str__(self):
        return self.name


FakeFighter = _FakeFighter()
FakeFighter.populate()


for fighter_data in _fighters:
    Fighter.add(*fighter_data)
