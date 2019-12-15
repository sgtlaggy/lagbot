import inspect

from .models import Fighter

MODES = {}


class CheckResult:
    def __init__(self, result, message=None):
        self.result = result
        self.message = message

    def __bool__(self):
        return self.result

    def __str__(self):
        return self.message


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
    def pick_check(player, fighter):
        if player.game.is_banned(fighter):
            return CheckResult(False, f'{fighter} is banned.')
        return CheckResult(True)

    @staticmethod
    def ban_check(player, fighter):
        if player.game.is_banned(fighter):
            return CheckResult(False, f'{fighter} is already banned.')
        return CheckResult(True)


@mode
class Elimination:
    description = 'You may not pick any fighter you have already played.'

    @staticmethod
    def pick_check(player, fighter):
        if player.has_played(fighter):
            return CheckResult(False, f'You have already played {fighter}.')
        elif player.game.is_banned(fighter):
            return CheckResult(False, f'{fighter} is banned.')
        return CheckResult(True)

    @staticmethod
    def ban_check(player, fighter):
        if all(pl.has_played(fighter) for pl in player.game.players.values()):
            return CheckResult(False, f'Everyone has already played {fighter}.')
        elif player.game.is_banned(fighter):
            return CheckResult(False, f'{fighter} is already banned.')
        return CheckResult(True)


@mode
class Smashdown:
    description = 'You may not pick any fighter that has already been played.'

    @staticmethod
    def pick_check(player, fighter):
        for plyr in player.game.players.values():
            if plyr.has_played(fighter):
                return CheckResult(False, f'{fighter} has already been played.')
            elif plyr.has_banned(fighter):
                return CheckResult(False, f'{fighter} is banned.')
        return CheckResult(True)

    @staticmethod
    def ban_check(player, fighter):
        for plyr in player.game.players.values():
            if plyr.has_played(fighter):
                return CheckResult(False, f'{fighter} has already been played.')
            elif plyr.has_banned(fighter):
                return CheckResult(False, f'{fighter} is already banned.')
        return CheckResult(True)


@mode
class Smasharound:
    description = 'You may not pick any fighter that has already won.'

    @staticmethod
    def pick_check(player, fighter):
        game = player.game
        if game.is_banned(fighter):
            return CheckResult(False, f'{fighter} is banned.')
        for p in game.players.values():
            if fighter in [p.fighters[i] for i in p.wins] and isinstance(fighter, Fighter):
                return CheckResult(False, f'{fighter} has already won.')
        return CheckResult(True)

    @staticmethod
    def ban_check(player, fighter):
        game = player.game
        if game.is_banned(fighter):
            return CheckResult(False, f'{fighter} is already banned.')
        for p in game.players.values():
            if fighter in [p.fighters[i] for i in p.wins] and isinstance(fighter, Fighter):
                return CheckResult(False, f'{fighter} has already won.')
        return CheckResult(True)
