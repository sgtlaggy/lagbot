import string
import re

from discord.ext import commands
import discord

from .utils.errors import NotFound, ServerError, NotInDB
from .base import BaseCog
from .utils import utils

endpoint = "http://127.0.0.1:4444/owapi/v3/u/{btag}/"
BLOB = endpoint + "blob"
STATS = endpoint + "stats"
HEROES = endpoint + "heroes"
HEROES_QP = HEROES + "/quickplay"
HEROES_COMP = HEROES + "/competitive"

BTAG_RE = re.compile(r'<@!?([0-9]+)>$')

MODES = ('quick', 'quickplay', 'qp', 'unranked',
         'comp', 'competitive', 'ranked')

HERO_INFO = {'ana': {'color': 0xCCC2AE, 'name': 'Ana'},
             'bastion': {'color': 0x6E994D, 'name': 'Bastion'},
             'dva': {'color': 0xFF7FD1, 'name': 'D.Va'},
             'genji': {'color': 0x84FE01, 'name': 'Genji'},
             'hanzo': {'color': 0x938848, 'name': 'Hanzo'},
             'junkrat': {'color': 0xD39308, 'name': 'Junkrat'},
             'lucio': {'color': 0x8BEC22, 'name': 'L\N{LATIN SMALL LETTER U WITH ACUTE}cio'},
             'mccree': {'color': 0x8D3939, 'name': 'McCree'},
             'mei': {'color': 0x9ADBF4, 'name': 'Mei'},
             'mercy': {'color': 0xFFE16C, 'name': 'Mercy'},
             'pharah': {'color': 0x1B65C6, 'name': 'Pharah'},
             'reaper': {'color': 0x272725, 'name': 'Reaper'},
             'reinhardt': {'color': 0xAA958E, 'name': 'Reinhardt'},
             'roadhog': {'color': 0xC19477, 'name': 'Roadhog'},
             'soldier76': {'color': 0x5870B6, 'name': 'Soldier: 76'},
             'sombra': {'color': 0x000000, 'name': 'Sombra'},
             'symmetra': {'color': 0x5CECFF, 'name': 'Symmetra'},
             'torbjorn': {'color': 0xFF6200, 'name': 'Torbj\N{LATIN SMALL LETTER O WITH DIAERESIS}rn'},
             'tracer': {'color': 0xF8911B, 'name': 'Tracer'},
             'widowmaker': {'color': 0x6F6FAE, 'name': 'Widowmaker'},
             'winston': {'color': 0x4C505C, 'name': 'Winston'},
             'zarya': {'color': 0xF571A8, 'name': 'Zarya'},
             'zenyatta': {'color': 0xC79C00, 'name': 'Zenyatta'}
             }


class NotPlayed(Exception):
    pass


class InvalidBTag(Exception):
    pass


SYMBOLS = string.punctuation + ' '


def links_embed(tag, region, color=None):
    official = 'https://playoverwatch.com/en-us/career/pc/{}/{}'.format(region, tag)
    owapi = 'http://lag.b0ne.com/owapi/v3/u/{}/blob?format=json_pretty'.format(tag)
    webapp = 'http://lag.b0ne.com/ow/'
    desc = ' | '.join(['[Official Stats]({})',
                       '[Raw Stats]({})',
                       '[Raw Stats Landing Page]({})']).format(
                           official, owapi, webapp)
    return discord.Embed(description=desc, colour=color)


def validate_btag(btag):
    if btag == '' or '-' in btag:
        return btag
    split = btag.split('#')
    if len(split) != 2:
        return None
    tag, disc = split
    if 3 <= len(tag) <= 12 and \
            not any(s in tag for s in SYMBOLS) and \
            not tag[0].isdigit() and \
            disc.isdigit():
        return '-'.join([tag, disc])
    else:
        return None


def api_player_tag(arg):
    match = BTAG_RE.match(arg)
    if match is not None:
        return match.group(1)
    elif arg in MODES:
        return arg
    else:
        return validate_btag(arg)


def api_to_btag(tag):
    return tag[::-1].replace('-', '#', 1)[::-1]


def ow_mode(arg):
    if arg in MODES[:4]:
        return 'quickplay'
    return 'competitive'


def ow_level(overall_stats):
    total = overall_stats['prestige'] * 100
    total += overall_stats['level']
    return total


def ow_region(data):
    for region in ('us', 'kr', 'eu', 'any'):
        if data.get(region) is not None:
            return region


def time_str(decimal):
    hours, minutes = divmod(round(decimal * 60), 60)
    if hours:
        fmt = '{h} hour{hp}'
        if minutes:
            fmt += ', {m} minute{mp}'
    elif minutes:
        fmt = '{m} minute{mp}'
    else:
        fmt = '<1 minute'
    return fmt.format(h=hours, hp=utils.plural(hours),
                      m=minutes, mp=utils.plural(minutes))


def most_played(hero_dict):
    sort = sorted(hero_dict.items(), key=lambda kv: kv[1], reverse=True)
    for hero, played in sort:
        if hero != 'overwatchguidundefined':
            yield (hero, time_str(played))


class Overwatch(BaseCog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_stats(self, tag, end=BLOB):
        btag = api_to_btag(tag)
        status, data = await self.request(end.format(btag=tag), timeout=15)
        if status == 500:
            await self.bot.send_message(self.bot.owner, 'Blizzard broke OWAPI.\n' + data['exc'])
            raise ServerError('Blizzard broke something. Please wait a bit before trying again.')
        elif status != 200:
            raise NotFound("Couldn't get stats for {}.".format(btag))
        region = ow_region(data)
        if region is None:
            raise NotPlayed('{} has not played Overwatch.'.format(btag))
        data[region]['region'] = region
        return data[region]

    async def get_tag(self, ctx, tag):
        member_id = ctx.message.author.id
        tag = api_player_tag(tag)
        if tag is None:
            raise InvalidBTag('Invalid Battletag')
        if tag == '' or '-' not in tag:
            member_id = tag or member_id
            tag = await self.bot.db.fetchval('''
                SELECT btag FROM overwatch WHERE id = $1
                ''', member_id)
        if tag is None:
            raise NotInDB('Not in the db.')
        return tag, member_id

    async def get_mode(self, member_id):
        if '-' in member_id:
            mode = await self.bot.db.fetchval('''
                SELECT mode FROM overwatch WHERE btag = $1
                ''', member_id)
        else:
            mode = await self.bot.db.fetchval('''
                SELECT mode FROM overwatch WHERE id = $1
                ''', member_id)
        return mode

    async def get_tag_mode(self, ctx, tag, mode):
        if tag in MODES:
            mode = ow_mode(tag)
            tag, member_id = await self.get_tag(ctx, '')
        else:
            tag, member_id = await self.get_tag(ctx, tag)
            if mode is not None:
                mode = ow_mode(mode)
            else:
                mode = await self.get_mode(tag) or \
                    await self.get_mode(member_id) or \
                    'competitive'
        return tag, mode, member_id

    async def get_all(self, ctx, tag, mode, end=BLOB):
        tag, mode, _ = await self.get_tag_mode(ctx, tag, mode)
        data = await self.fetch_stats(tag, end)
        if mode == 'competitive' and not data['stats'].get(mode) and \
                not data['heroes']['stats'][mode]:
            mode = 'quickplay'
        return data['stats'].get(mode), data['heroes']['playtime'][mode], \
            tag, mode, data['region']

    @commands.group(aliases=['ow'], pass_context=True, invoke_without_command=True)
    async def overwatch(self, ctx, tag='', mode=None):
        """See stats of yourself or another player.

        [tag] can be either BattleTag or a mention to someone in the db
        [mode] can be 'quick', 'quickplay', 'qp', 'unranked',
                      'comp', 'competitive', 'ranked'
             * Defaults to competitive stats, falls back to quickplay.

        Stats by Battletag            : !ow BattleTag#1234
        Stats by Discord mention      : !ow @DiscordName
        Add yourself to database      : !ow set BattleTag#1234
        Remove yourself from database : !ow unset
        Hero Play Time                : !ow heroes BattleTag#1234
        Own Stats, Different mode     : !ow [optional-set/heroes] qp/comp

        Notes
            * If you are in the DB you can replace your battletag to get/change
                your own stats with a mode different than you have saved.
            * You can follow BattleTag/Discord mention with a mode of gameplay
                to force getting quickplay/competitive stats.
            * BattleTags are case-sensitive.
            * To get stats by Discord mention, the person must be in the DB.
        """
        try:
            await self.bot.type()
            stats, heroes, tag, mode, region = await self.get_all(ctx, tag, mode)
        except (NotFound, ServerError, NotInDB, NotPlayed, InvalidBTag) as e:
            await self.bot.say(e)
            return

        mp_hero, mp_time = next(most_played(heroes))

        message = ['{} stats:'.format(mode.title())]
        lines = [
            ('Battletag', api_to_btag(tag)),
            ('Time Played', time_str(stats['game_stats']['time_played'])),
            ('Level', ow_level(stats['overall_stats']))
        ]
        if mode == 'competitive':
            lines.append(('Competitive Rank',
                          stats['overall_stats']['comprank'] or 'Unranked'))
        lines.append(('Most Played Hero', HERO_INFO[mp_hero]['name']))
        lines.append(('Hero Time', mp_time))
        if stats['overall_stats'].get('games'):
            lines.extend([
                ('Games Played', stats['overall_stats']['games']),
                ('Games Won', stats['overall_stats']['wins']),
                ('Win Rate', '{}%'.format(stats['overall_stats']['win_rate']))
            ])
        else:
            lines.append(('Games Won', stats['overall_stats']['wins']))
        lines.append(('Kill/Death', round(stats['game_stats']['kpd'], 2)))
        lines.append(('Environmental Deaths',
                      int(stats['game_stats'].get('environmental_deaths', 0))))
        message.append('```ocaml')
        width = max(len(k) for k, v in lines)
        for line in lines:
            message.append('{0:<{width}} : {1}'.format(*line, width=width))
        message.append('```')
        embed = links_embed(tag, region, HERO_INFO[mp_hero]['color'])
        await self.bot.say('\n'.join(message), embed=embed)

    @overwatch.command(pass_context=True)
    async def heroes(self, ctx, tag='', mode=None):
        """Get playtime for each played hero.

        [tag] can be either BattleTag or a mention to someone in the db
        [mode] can be 'quick', 'quickplay', 'qp', 'comp', or 'competitive'
             * Defaults to competitive stats, falls back to quickplay.
        """
        try:
            await self.bot.type()
            _, heroes, tag, mode, region = await self.get_all(ctx, tag, mode, HEROES)
        except (NotFound, ServerError, NotInDB, NotPlayed, InvalidBTag) as e:
            await self.bot.say(e)
            return

        message = ['{} hero stats:'.format(mode.title())]
        width = max(len(k) for k in heroes.keys())
        message.append('```ocaml')
        ordered = list(most_played(heroes))
        for hero, played in ordered:
            if played:
                message.append('{0:<{width}} : {1}'.format(
                    HERO_INFO[hero]['name'],
                    played,
                    width=width))
        message.append('```')
        hero = ordered[0][0]
        embed = links_embed(tag, region, HERO_INFO[hero]['color'])
        await self.bot.say('\n'.join(message), embed=embed)

    @overwatch.command(name='set', aliases=['save'], pass_context=True)
    async def ow_set(self, ctx, tag, mode=None):
        """Set your battletag and default gamemode.

        <tag> is your BattleTag
        [mode] can be 'quick', 'quickplay', 'qp', 'comp', or 'competitive'
             * Defaults to competitive stats, falls back to quickplay.

        Note:
        If you're already in the db, you can use this command again as follows:
            set [mode] - change preferred mode
            set <tag>  - change battletag
            set <tag> [mode] - change BattleTag and preferred mode
        """
        author_id = ctx.message.author.id
        in_db = bool(await self.bot.db.fetchval('''
            SELECT id FROM overwatch WHERE id = $1
            ''', author_id))
        if in_db and mode is None and tag in MODES:
            new_tag, new_mode, _ = await self.get_tag_mode(ctx, tag, mode)
        else:
            new_tag = validate_btag(tag)
            if new_tag is None:
                await self.bot.say('Invalid Battletag')
            new_mode = ow_mode(mode)
        async with self.bot.db.transaction():
            if in_db and mode is None and tag in MODES:
                await self.bot.db.execute('''
                    UPDATE overwatch SET mode = $1 WHERE id = $2
                    ''', new_mode, author_id)
                message = '\N{THUMBS UP SIGN} Updated preferred mode.'
            elif in_db and mode is None and tag not in MODES:
                await self.bot.db.execute('''
                    UPDATE overwatch SET btag = $1 WHERE id = $2
                    ''', new_tag, author_id)
                message = '\N{THUMBS UP SIGN} Updated Battletag.'
            elif in_db:
                await self.bot.db.execute('''
                    UPDATE overwatch SET (btag, mode) = ($1, $2) WHERE id = $3
                    ''', new_tag, new_mode, author_id)
                message = '\N{THUMBS UP SIGN} Updated Battletag and preferred mode.'
            else:
                await self.bot.db.execute('''
                    INSERT INTO overwatch (id, btag, mode) VALUES ($1, $2, $3)
                    ''', author_id, new_tag, new_mode)
                message = '\N{THUMBS UP SIGN} Added to db.'
        await self.bot.say(message)

    @overwatch.command(name='unset', aliases=['delete', 'remove'], pass_context=True)
    async def ow_unset(self, ctx):
        """Remove your battletag from the DB."""
        author_id = ctx.message.author.id
        in_db = bool(await self.bot.db.fetchval('''
            SELECT id FROM overwatch WHERE id = $1
            ''', author_id))
        if in_db:
            async with self.bot.db.transaction():
                await self.bot.db.execute('''
                    DELETE FROM overwatch WHERE id = $1
                    ''', author_id)
            message = '\N{THUMBS UP SIGN} Removed from db.'
        else:
            message = '\N{THUMBS DOWN SIGN} Not in db.'
        await self.bot.say(message)


def setup(bot):
    bot.add_cog(Overwatch(bot))
