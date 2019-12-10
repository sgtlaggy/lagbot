import inspect

from .models import Fighter

MODES = {}


def inject_help_modes(func):
    modes = [f'{m.name} - {m.description}' for m in MODES.values()]
    doc = inspect.getdoc(func)
    func.__doc__ = doc.format(modes='\n'.join(modes))
    return func


def mode(cls):
    cls.name = name = cls.__name__
    MODES[name.lower()] = cls


@mode
class Smash:
    description = 'You may pick any fighter.'

    @staticmethod
    def _check(player, fighter):
        return not player.game.is_banned(fighter)

    pick_check = _check
    ban_check = _check


@mode
class Elimination:
    description = 'You may not pick any fighter you have already played.'

    @staticmethod
    def pick_check(player, fighter):
        return not (player.has_played(fighter) or player.game.is_banned(fighter))

    @staticmethod
    def ban_check(player, fighter):
        return not (all(pl.has_played(fighter) for pl in player.game.players.values())
                    or player.game.is_banned(fighter))


@mode
class Smashdown:
    description = 'You may not pick any fighter that has already been played.'

    @staticmethod
    def _check(player, fighter):
        for plyr in player.game.players.values():
            if plyr.has_played(fighter) or plyr.has_banned(fighter):
                return False
        return True

    pick_check = _check
    ban_check = _check


@mode
class Smasharound:
    description = 'You may not pick any fighter that has already won.'

    @staticmethod
    def _check(player, fighter):
        game = player.game
        if game.is_banned(fighter):
            return False
        for p in game.players.values():
            if fighter in [p.fighters[i] for i in p.wins] and isinstance(fighter, Fighter):
                return False
        return True

    pick_check = _check
    ban_check = _check
