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

BTAG_RE = re.compile(r'<@!?([0-9]+)>$')

MODES = ('quick', 'quickplay', 'qp', 'unranked',
         'comp', 'competitive', 'ranked')

HERO_INFO = {'ana': {'color': 0xCCC2AE, 'name': 'Ana'},
             'bastion': {'color': 0x6E994D, 'name': 'Bastion'},
             'dva': {'color': 0xFF7FD1, 'name': 'D.Va'},
             'genji': {'color': 0x84FE01, 'name': 'Genji'},
             'hanzo': {'color': 0x938848, 'name': 'Hanzo'},
             'junkrat': {'color': 0xD39308, 'name': 'Junkrat'},
             'lucio': {'color': 0x8BEC22, 'name': 'Lúcio'},
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
             'torbjorn': {'color': 0xFF6200, 'name': 'Torbjörn'},
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


class portrait:
    default = 'https://blzgdapipro-a.akamaihd.net/hero/{}/hero-select-portrait{}.png'

    @classmethod
    def get(cls, hero):
        if hero not in {'soldier76', 'sombra'}:
            return cls.default.format(hero, '')
        elif hero == 'soldier76':
            return cls.default.format('soldier-76', '')
        elif hero == 'sombra':
            return cls.default.format(hero, '-d5121256f71c9d7dc7a434ac75be95d99942e8386ba7f8462f3e15d91223854c9b9adde42a3aca70715ab24326a7c27848151e8ab92a259ac7744d7f15a6d91b')


def stat_links(tag, region):
    return dict(official='https://playoverwatch.com/en-us/career/pc/{}/{}'.format(region, tag),
                owapi='http://lag.b0ne.com/owapi/v3/u/{}/blob?format=json_pretty'.format(tag),
                webapp='http://lag.b0ne.com/ow/')


SYMBOLS = string.punctuation + ' '


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
    for region in {'us', 'kr', 'eu', 'any'}:
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
    async def fetch_stats(self, tag, end=BLOB):
        btag = api_to_btag(tag)
        status, data = await self.bot.request(end.format(btag=tag), timeout=15)
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
            raise InvalidBTag('Invalid BattleTag')
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

        Stats by BattleTag            : !ow BattleTag#1234
        Stats by Discord mention      : !ow @DiscordName
        Add yourself to database      : !ow set BattleTag#1234
        Remove yourself from database : !ow unset
        Hero Play Time                : !ow heroes BattleTag#1234
        Own Stats, Different mode     : !ow [optional-set/heroes] qp/comp

        Notes
            * You can click the BattleTag to go to that person's official stats page.
            * If you are in the DB you can replace your BattleTag to get/change your own stats with a mode different than you have saved.
            * You can follow BattleTag/Discord mention with a mode of gameplay to force getting quickplay/competitive stats.
            * BattleTags are case-sensitive.
            * To get stats by Discord mention, the person must be in the DB.
        """
        await self.bot.type()
        try:
            stats, heroes, tag, mode, region = await self.get_all(ctx, tag, mode)
        except (NotFound, ServerError, NotInDB, NotPlayed, InvalidBTag) as e:
            await self.bot.say(e)
            return

        mp_hero, mp_time = next(most_played(heroes))
        embed = discord.Embed(colour=HERO_INFO[mp_hero]['color'])
        links = stat_links(tag, region)
        embed.description = '**{} Stats** ([raw]({}))'.format(mode.title(), links['owapi'])
        embed.set_author(name=api_to_btag(tag),
                         icon_url=stats['overall_stats']['avatar'],
                         url=links['official'])
        embed.set_thumbnail(url=portrait.get(mp_hero))
        embed.add_field(name='Time Played', value=time_str(stats['game_stats']['time_played']))
        embed.add_field(name='Level', value=ow_level(stats['overall_stats']))
        if mode == 'competitive':
            embed.add_field(name='Competitive Rank',
                            value=stats['overall_stats']['comprank'] or 'Unranked')
        embed.add_field(name='Most Played Hero', value=' - '.join([HERO_INFO[mp_hero]['name'], mp_time]))
        if stats['overall_stats'].get('games'):
            embed.add_field(name='Games Played', value=stats['overall_stats']['games'])
            embed.add_field(name='Games Won', value=stats['overall_stats']['wins'])
            embed.add_field(name='Games Tied', value=stats['overall_stats']['ties'])
            embed.add_field(name='Win Rate', value='{}%'.format(stats['overall_stats']['win_rate']))
        else:
            embed.add_field(name='Games Won', value=stats['overall_stats']['wins'])
        embed.add_field(name='Kill/Death', value=round(stats['game_stats']['kpd'], 2))
        embed.add_field(name='Environmental Deaths',
                        value=int(stats['game_stats'].get('environmental_deaths', 0)))
        await self.bot.say(embed=embed)

    @overwatch.command(pass_context=True)
    async def heroes(self, ctx, tag='', mode=None):
        """Get playtime for each played hero.

        [tag] can be either BattleTag or a mention to someone in the db
        [mode] can be 'quick', 'quickplay', 'qp', 'comp', or 'competitive'
             * Defaults to competitive stats, falls back to quickplay.
        """
        await self.bot.type()
        try:
            stats, heroes, tag, mode, region = await self.get_all(ctx, tag, mode)
        except (NotFound, ServerError, NotInDB, NotPlayed, InvalidBTag) as e:
            await self.bot.say(e)
            return

        message = ['{} hero stats:'.format(mode.title())]
        width = max(len(HERO_INFO[hero]['name']) for hero in heroes.keys())
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
        links = stat_links(tag, region)
        embed = discord.Embed(colour=HERO_INFO[hero]['color'])
        embed.set_author(name=api_to_btag(tag),
                         icon_url=stats['overall_stats']['avatar'],
                         url=links['official'])
        await self.bot.say('\n'.join(message), embed=embed)

    @overwatch.command(name='set', aliases=['save'], pass_context=True)
    async def ow_set(self, ctx, tag, mode=None):
        """Set your BattleTag and default gamemode.

        <tag> is your BattleTag
        [mode] can be 'quick', 'quickplay', 'qp', 'comp', or 'competitive'
             * Defaults to competitive stats, falls back to quickplay.

        Note:
        If you're already in the db, you can use this command again as follows:
            set [mode] - change preferred mode
            set <tag>  - change BattleTag
            set <tag> [mode] - change BattleTag and preferred mode
        """
        author = ctx.message.author
        rec = await self.bot.db.fetchrow('''
            SELECT * FROM overwatch WHERE id = $1
            ''', author.id)
        if rec is not None:
            if mode is None and tag in MODES:
                new_tag = rec['btag']
                new_mode = ow_mode(tag)
            else:
                new_tag = validate_btag(tag)
                if new_tag is None:
                    await self.bot.say('Invalid BattleTag or mode.')
                    return
                if mode in MODES:
                    new_mode = ow_mode(mode)
                else:
                    new_mode = rec['mode']
        else:
            new_tag = validate_btag(tag)
            new_mode = ow_mode(mode)
        async with self.bot.db.transaction():
            await self.bot.db.execute('''
                INSERT INTO overwatch (id, btag, mode) VALUES ($1, $2, $3)
                ON CONFLICT (id)
                DO UPDATE SET (btag, mode) = ($2, $3)
                ''', author.id, new_tag, new_mode)
        if not rec:
            message = 'Added to db.'
        elif mode is None:
            if tag in MODES:
                message = 'Updated preferred mode.'
            else:
                message = 'Updated BattleTag.'
        else:
            message = 'Updated BattleTag and preferred mode.'
        await self.bot.say('\N{THUMBS UP SIGN} ' + message)

    @overwatch.command(name='unset', aliases=['delete', 'remove'], pass_context=True)
    async def ow_unset(self, ctx):
        """Remove your BattleTag from the DB."""
        author = ctx.message.author
        in_db = bool(await self.bot.db.fetchval('''
            SELECT id FROM overwatch WHERE id = $1
            ''', author.id))
        if in_db:
            async with self.bot.db.transaction():
                await self.bot.db.execute('''
                    DELETE FROM overwatch WHERE id = $1
                    ''', author.id)
            message = '\N{THUMBS UP SIGN} Removed from db.'
        else:
            message = '\N{THUMBS DOWN SIGN} Not in db.'
        await self.bot.say(message)


def setup(bot):
    bot.add_cog(Overwatch(bot))
