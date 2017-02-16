import string
import enum
import re

from discord.ext import commands
import asyncpg
import discord

from utils.errors import NotFound, ServerError, NotInDB
from utils.utils import pluralize
from cogs.base import BaseCog


endpoint = "http://127.0.0.1:4444/owapi/v3/u/{btag}/"
BLOB = endpoint + "blob"
STATS = endpoint + "stats"
HEROES = endpoint + "heroes"

BTAG_RE = re.compile(r'<@!?([0-9]+)>$')

REGIONS = ('us', 'eu', 'kr', 'any')


class Mode(enum.Enum):
    quickplay = 0
    unranked = 0
    quick = 0
    qp = 0
    competitive = 1
    ranked = 1
    comp = 1
    default = 1


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
             'zenyatta': {'color': 0xC79C00, 'name': 'Zenyatta'}}


class NotPlayed(Exception):
    pass


class InvalidBTag(Exception):
    pass


class Rank:
    default = 'https://blzgdapipro-a.akamaihd.net/game/rank-icons/season-2/rank-{}.png'
    ranks = {'bronze': 1,
             'silver': 2,
             'gold': 3,
             'platinum': 4,
             'diamond': 5,
             'master': 6,
             'grandmaster': 7}

    @classmethod
    def get(cls, rank):
        return cls.default.format(cls.ranks[rank])


class Portrait:
    default = 'https://blzgdapipro-a.akamaihd.net/hero/{}/hero-select-portrait{}.png'

    @classmethod
    def get(cls, hero):
        if hero not in {'soldier76', 'sombra'}:
            return cls.default.format(hero, '')
        elif hero == 'soldier76':
            return cls.default.format('soldier-76', '')
        elif hero == 'sombra':  # blame Blizzard
            return cls.default.format(hero, '-d5121256f71c9d7dc7a434ac75be95d99942e8386ba7f8462f3e15d91223854c9b9adde42a3aca70715ab24326a7c27848151e8ab92a259ac7744d7f15a6d91b')


def stat_links(tag, region):
    return dict(official=f'https://playoverwatch.com/en-us/career/pc/{region}/{tag}',
                owapi=f'http://lag.b0ne.com/owapi/v3/u/{tag}/blob?format=json_pretty',
                webapp='http://lag.b0ne.com/ow/')


SYMBOLS = string.punctuation + ' '


def fix_arg_order(*args):
    tag, mode, region = '', None, None
    for arg in args:
        if arg is None or isinstance(arg, Mode):
            continue
        elif any(char in arg for char in {'#', '@'}):
            tag = arg
        elif arg.lower() in REGIONS:
            region = arg.lower()
        else:
            try:
                Mode[arg.lower()]
                mode = arg.lower()
            except KeyError:
                pass
    return tag, mode, region


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
    return validate_btag(arg)


def api_to_btag(tag):
    return tag[::-1].replace('-', '#', 1)[::-1]


def ow_mode(arg):
    try:
        return Mode[arg.lower()]
    except KeyError:
        raise NotFound(f'{arg} is not a valid mode.')


def ow_level(overall_stats):
    total = overall_stats['prestige'] * 100
    total += overall_stats['level']
    return total


def time_str(decimal):
    hours, minutes = divmod(round(decimal * 60), 60)
    if hours:
        fmt = '{h} hour{{}}'
        if minutes:
            fmt += ', {m} minute{{}}'
    elif minutes:
        fmt = '{m} minute{{}}'
    else:
        fmt = '<1 minute'
    return pluralize(fmt.format(h=hours, m=minutes))


def most_played(hero_dict):
    sort = sorted(hero_dict.items(), key=lambda kv: kv[1], reverse=True)
    for hero, played in sort:
        if hero != 'overwatchguidundefined':
            yield (hero, time_str(played))


class Overwatch(BaseCog):
    """Commands for getting Overwatch stats.

    Any command argument named "tag" is a case-sensitive BattleTag.
    Any command argument named "mode" is a gamemode (qp, comp, quickplay, competitive, unranked, ranked).
    Any command argument named "region" is a region (us, eu, kr).
    """
    async def fetch_stats(self, tag, end=BLOB):
        btag = api_to_btag(tag)
        status, data = await self.bot.request(end.format(btag=tag), timeout=15)
        if status == 500:
            await self.bot.owner.send(f'Blizzard broke OWAPI.\n{data["exc"]}')
            raise ServerError('Blizzard broke something. Please wait a bit before trying again.')
        elif status != 200:
            raise NotFound(f"Couldn't get stats for {btag}.")
        return data

    async def get_region(self, tag, region, data):
        if region is not None:
            if data.get(region.lower()) is not None:
                return region.lower()
            else:
                raise NotFound(f'{api_to_btag(tag)} has not played in {region}.')
        available = [r for r in REGIONS if data.get(r) is not None]
        rec = await self.bot.db.fetchrow('''
            SELECT region FROM overwatch WHERE btag = $1
            ''', tag)
        if rec is None:
            if available:
                return available[0]
            raise NotPlayed(f'{api_to_btag(tag)} has not played Overwatch.')
        return rec['region']

    async def get_tag(self, ctx, tag):
        member_id = ctx.author.id
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
        if mode is not None:
            return Mode[mode]

    async def get_tag_mode(self, ctx, tag, mode):
        try:
            Mode[tag.lower()]
        except KeyError:
            tag, member_id = await self.get_tag(ctx, tag)
            if mode is not None:
                mode = ow_mode(mode)
            else:
                mode = await self.get_mode(tag) or \
                    await self.get_mode(member_id) or \
                    Mode.default
        else:
            mode = ow_mode(tag)
            tag, member_id = await self.get_tag(ctx, '')
        return tag, mode, member_id

    async def get_all(self, ctx, tag, mode, reg, end=BLOB):
        tag, mode, _ = await self.get_tag_mode(ctx, tag, mode)
        data = await self.fetch_stats(tag, end)
        region = await self.get_region(tag, reg, data)
        data = data[region]
        if mode is Mode.competitive and \
                not data['stats'].get(mode.name) and \
                not data['heroes']['stats'][mode.name]:
            mode = Mode.quickplay
        return data['stats'].get(mode.name), \
            data['heroes']['playtime'][mode.name], \
            tag, mode, region

    @commands.group(aliases=['ow'], usage='[tag] [mode] [region]', invoke_without_command=True)
    async def overwatch(self, ctx, *args):
        """See stats of yourself or another player.

        [tag], [mode], and [region] can be specified in any order.
        [tag] can be either BattleTag or a mention to someone in the db
        [mode] can be 'quick', 'quickplay', 'qp', 'unranked',
                      'comp', 'competitive', 'ranked'
             * Defaults to competitive stats, falls back to quickplay.
        [region] can be 'us', 'eu', or 'kr'

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
        tag, mode, region = fix_arg_order(*args)
        with ctx.typing():
            stats, heroes, tag, mode, region = await self.get_all(ctx, tag, mode, region)

            mp_hero, mp_time = next(most_played(heroes))
            embed = discord.Embed(colour=HERO_INFO[mp_hero]['color'])
            links = stat_links(tag, region)
            embed.description = f'**{mode.name.title()} Stats** ([raw]({links["owapi"]}))'
            author_icon = stats['overall_stats']['avatar']
            embed.set_thumbnail(url=Portrait.get(mp_hero))
            embed.add_field(name='Time Played', value=time_str(stats['game_stats']['time_played']))
            embed.add_field(name='Level', value=ow_level(stats['overall_stats']))
            if stats['competitive']:
                tier = stats['overall_stats']['tier']
                if tier is not None:
                    rank = '{0[tier]} {0[comprank]}'.format(stats['overall_stats']).title()
                    author_icon = Rank.get(tier)
                else:
                    rank = 'Unranked'
                embed.add_field(name='Competitive Rank', value=rank)
            embed.add_field(name='Most Played Hero', value=' - '.join([HERO_INFO[mp_hero]['name'], mp_time]))
            if stats['overall_stats'].get('games'):
                embed.add_field(name='Games Played', value=stats['overall_stats']['games'])
                embed.add_field(name='Games Won', value=stats['overall_stats']['wins'])
                embed.add_field(name='Games Tied', value=stats['overall_stats']['ties'])
                embed.add_field(name='Win Rate', value=f'{stats["overall_stats"]["win_rate"]}%')
            else:
                embed.add_field(name='Games Won', value=stats['overall_stats']['wins'])
            embed.add_field(name='Kill/Death', value=round(stats['game_stats']['kpd'], 2))
            embed.add_field(name='Environmental Deaths',
                            value=int(stats['game_stats'].get('environmental_deaths', 0)))
            embed.set_author(name=api_to_btag(tag),
                             icon_url=author_icon,
                             url=links['official'])
        await ctx.send(embed=embed)

    @overwatch.command(usage='[tag] [mode] [region]')
    async def heroes(self, ctx, *args):
        """Get playtime for each played hero.

        [tag], [mode], and [region] can be specified in any order.
        [tag] can be either BattleTag or a mention to someone in the db
        [mode] can be 'quick', 'quickplay', 'qp', 'unranked',
                      'comp', 'competitive', 'ranked'
             * Defaults to competitive stats, falls back to quickplay.
        [region] can be 'us', 'eu', or 'kr'
        """
        tag, mode, region = fix_arg_order(*args)
        with ctx.typing():
            stats, heroes, tag, mode, region = await self.get_all(ctx, tag, mode, region)

            message = [f'{mode.name.title()} hero stats:']
            width = max(len(HERO_INFO[hero]['name']) for hero in heroes.keys())
            message.append('```ocaml')
            ordered = list(most_played(heroes))
            for hero, played in ordered:
                if played:
                    message.append(f'{HERO_INFO[hero]["name"]:<{width}} : {played}')
            message.append('```')
            hero = ordered[0][0]
            links = stat_links(tag, region)
            embed = discord.Embed(colour=HERO_INFO[hero]['color'])
            tier = stats['overall_stats']['tier']
            if stats['competitive'] and tier is not None:
                author_icon = Rank.get(tier)
            else:
                author_icon = stats['overall_stats']['avatar']
            embed.set_author(name=api_to_btag(tag),
                             icon_url=author_icon,
                             url=links['official'])
        await ctx.send('\n'.join(message), embed=embed)

    @overwatch.group(name='set', aliases=['save'], invoke_without_command=True)
    async def ow_set(self, ctx, tag, mode=None, region=None):
        """Set your BattleTag and default gamemode.

        <tag>, [mode], and [region] can be specified in any order.
        <tag> can be either BattleTag or a mention to someone in the db
        [mode] can be 'quick', 'quickplay', 'qp', 'unranked',
                      'comp', 'competitive', 'ranked'
             * Defaults to competitive stats, falls back to quickplay.
        [region] can be 'us', 'eu', or 'kr'

        Note:
        If you're already in the db, you can use this command again as follows:
            set tag <tag>   - change BattleTag
            set mode <mode> - change preferred mode
            set region <region> - change preffered region
        """
        author = ctx.author
        tag, mode, region = fix_arg_order(tag, mode, region)
        new_tag = validate_btag(tag)
        new_mode = ow_mode(mode)
        new_region = region or 'us'
        try:
            async with self.bot.db.transaction():
                await self.bot.db.execute('''
                    INSERT INTO overwatch (id, btag, mode, region) VALUES ($1, $2, $3, $4)
                    ''', author.id, new_tag, new_mode.name, new_region)
        except asyncpg.UniqueViolationError:
            await ctx.send("You're already in the db. Use subcommands to change your info.")
        else:
            await ctx.send('\N{THUMBS UP SIGN} Added to the db.')

    @ow_set.command(name='tag', aliases=['btag', 'battletag'])
    async def set_tag(self, ctx, tag):
        """Change your BattleTag in the db."""
        new_tag = validate_btag(tag)
        if new_tag is None:
            await ctx.send(f'{tag} is not a valid BattleTag.')
            return
        async with self.bot.db.transaction():
            res = await self.bot.db.execute('''
                UPDATE overwatch SET btag = $1 WHERE id = $2
                ''', new_tag, ctx.author.id)
        if res[-1] == '0':
            await ctx.send("\N{THUMBS DOWN SIGN} You're not in the db.")
        else:
            await ctx.send('\N{THUMBS UP SIGN} Updated your BattleTag.')

    @ow_set.command(name='mode')
    async def set_mode(self, ctx, mode):
        """Change your preferred mode in the db."""
        new_mode = ow_mode(mode)
        async with self.bot.db.transaction():
            res = await self.bot.db.execute('''
                UPDATE overwatch SET mode = $1 WHERE id = $2
                ''', new_mode.name, ctx.author.id)
        if res[-1] == '0':
            await ctx.send("\N{THUMBS DOWN SIGN} You're not in the db.")
        else:
            await ctx.send('\N{THUMBS UP SIGN} Updated your preferred mode.')

    @ow_set.command(name='region')
    async def set_region(self, ctx, region):
        """Change your preferred region in the db."""
        if region.lower() in REGIONS:
            new_region = region.lower()
        else:
            await ctx.send(f'{region} is not a valid region.')
            return
        async with self.bot.db.transaction():
            res = await self.bot.db.execute('''
                UPDATE overwatch SET region = $1 WHERE id = $2
                ''', new_region, ctx.author.id)
        if res[-1] == '0':
            await ctx.send("\N{THUMBS DOWN SIGN} You're not in the db.")
        else:
            await ctx.send('\N{THUMBS UP SIGN} Updated your region.')

    @overwatch.command(name='unset', aliases=['delete', 'remove'])
    async def ow_unset(self, ctx):
        """Remove your BattleTag from the DB."""
        author = ctx.author
        async with self.bot.db.transaction():
            res = await self.bot.db.execute('''
                DELETE FROM overwatch WHERE id = $1
                ''', author.id)
        if res[-1] == '0':
            await ctx.send("\N{THUMBS DOWN SIGN} You're not in the db.")
        else:
            await ctx.send('\N{THUMBS UP SIGN} Removed from the db.')

    async def __error(self, exc, ctx):
        if not isinstance(exc, commands.CommandInvokeError):
            exc.handled = False
            return
        if isinstance(exc.original, (NotFound, ServerError, NotInDB, NotPlayed, InvalidBTag)):
            exc.handled = True
            await ctx.send(exc.original)
            return


def setup(bot):
    bot.add_cog(Overwatch(bot))
