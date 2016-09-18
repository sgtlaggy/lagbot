import re

from discord.ext import commands
import aiohttp

from .utils.utils import NotFound, NotInDB, init_db
from .utils import utils

# self-hosting OWAPI until Fuyu updates
endpoint = "http://127.0.0.1:4444/api/v3/u/{btag}/"
BLOB = endpoint + "blob"
STATS = endpoint + "stats"
HEROES = endpoint + "heroes"
HEROES_QP = HEROES + "/quickplay"
HEROES_COMP = HEROES + "/competitive"

TIERS = ('quick', 'quickplay', 'qp', 'unranked',
         'comp', 'competitive', 'ranked')


def player_tag(arg):
    match = re.match(r'<@!?([0-9]+)>$', arg)
    if match is not None:
        return match.group(1)
    else:
        return arg[::-1].replace('#', '-', 1)[::-1]


def ow_tier(arg):
    if arg in TIERS[:4]:
        return 'quickplay'
    return 'competitive'


def ow_level(overall_stats):
    total = overall_stats['prestige'] * 100
    total += overall_stats['level']
    return total


def ow_region(data):
    for region in ('us', 'kr', 'eu', 'any'):
        if data[region] is not None:
            return region


def time_from_decimal(dec):
    return divmod(round(dec * 60), 60)


def most_played(hero_dict):
    for hero, played in sorted(hero_dict.items(),
                               key=lambda kv: kv[1],
                               reverse=True):
        return hero.title(), time_from_decimal(played)


def time_str(tupdec):
    if isinstance(tupdec, tuple):
        hours, minutes = tupdec
    else:
        hours, minutes = time_from_decimal(tupdec)
    if hours:
        fmt = '{h} hour{hp}, {m} minute{mp}'
    elif minutes:
        fmt = '{m} minute{mp}'
    else:
        fmt = '<1 minute'
    return fmt.format(h=hours, hp=utils.plural(hours),
                      m=minutes, mp=utils.plural(minutes))


class Overwatch:
    def __init__(self, bot):
        self.bot = bot
        bot.loop.run_until_complete(init_db(
            bot, 'overwatch',
            'id   text PRIMARY KEY',
            'btag text',
            'tier text'))

    async def fetch_stats(self, tag, tier, end=BLOB):
        with aiohttp.Timeout(10):
            async with self.bot.aiohsession.get(end.format(btag=tag)) as resp:
                status, data = resp.status, await resp.json()
        if status == 404:
            raise NotFound
        return data[ow_region(data)]

    async def get_tag(self, ctx, tag):
        member_id = ctx.message.author.id
        tag = player_tag(tag)
        if tag == '' or '-' not in tag:
            member_id = tag or member_id
            tag = await self.bot.db.fetchval('''
                SELECT btag FROM overwatch WHERE id = $1
                ''', member_id)
        if tag is None:
            raise NotInDB
        return tag, member_id

    async def get_tier(self, member_id):
        if '-' in member_id:
            tier = await self.bot.db.fetchval('''
                SELECT tier FROM overwatch WHERE btag = $1
                ''', member_id)
        else:
            tier = await self.bot.db.fetchval('''
                SELECT tier FROM overwatch WHERE id = $1
                ''', member_id)
        return tier

    async def get_tag_tier(self, ctx, tag, tier):
        if tag in TIERS:
            tier = ow_tier(tag)
            tag, member_id = await self.get_tag(ctx, '')
        else:
            tag, member_id = await self.get_tag(ctx, tag)
            if tier is not None:
                tier = ow_tier(tier)
            else:
                tier = await self.get_tier(tag) or \
                    await self.get_tier(member_id) or \
                    'competitive'
        return tag, tier, member_id

    async def get_all(self, ctx, tag, tier, end=BLOB):
        tag, tier, _ = await self.get_tag_tier(ctx, tag, tier)
        data = await self.fetch_stats(tag, tier, end)
        if tier == 'competitive' and not data['stats'].get(tier, {}) and \
                not data['heroes']['stats'][tier]:
            tier = 'quickplay'
        return data['stats'].get(tier, {}), \
            data['heroes']['playtime'][tier], tag, tier

    @commands.group(aliases=['ow'], pass_context=True,
                    invoke_without_command=True)
    async def overwatch(self, ctx, tag: player_tag = '', tier=None):
        """See stats of yourself or another player.

        [tag] can be either BattleTag or a mention to someone in the db
        [tier] can be 'quick', 'quickplay', 'qp', 'unranked',
                      'comp', 'competitive', 'ranked'
             * Defaults to competitive stats, falls back to quickplay.

        Stats by Battletag        : !ow BattleTag#1234
        Stats by Discord mention  : !ow @DiscordName
        Add yourself to database  : !ow set BattleTag#1234
        Hero Play Time            : !ow heroes BattleTag#1234
        Own Stats, Different Tier : !ow [optional-set/heroes] qp/comp

        Notes
            * If you are in the DB you can replace your battletag to get/change
                your own stats with a tier different than you have saved.
            * You can follow BattleTag/Discord mention with a tier of gameplay
                to force getting quickplay/competitive stats.
            * BattleTags are case-sensitive.
            * To get stats by Discord mention, the person must be in the DB.
        """
        try:
            stats, heroes, tag, tier = await self.get_all(ctx, tag, tier)
        except NotInDB:
            await self.bot.say("Not in the db.")
            return

        mp_hero, mp_time = most_played(heroes)

        message = ['{} stats:'.format(tier.title())]
        lines = [
            ('Battletag', tag[::-1].replace('-', '#', 1)[::-1]),
            ('Time played', time_str(stats['game_stats']['time_played'])),
            ('Level', ow_level(stats['overall_stats']))
        ]
        if tier == 'competitive':
            lines.append(('Competitive Rank',
                          stats['overall_stats']['comprank'] or 'Unranked'))
        lines.append(('Most Played Hero', mp_hero))
        lines.append(('Hero Time', time_str(mp_time)))
        if stats['overall_stats']['games']:
            lines.extend([
                ('Games Played', stats['overall_stats']['games']),
                ('Games Won', stats['overall_stats']['wins']),
                ('Win Rate', '{}%'.format(stats['overall_stats']['win_rate']))
            ])
        else:
            lines.append(('Games Won', stats['overall_stats']['wins']))
        lines.append(('Kill/death', round(stats['game_stats']['kpd'], 2)))
        lines.append(('Environmental Deaths',
                      int(stats['game_stats'].get('environmental_deaths', 0))))
        message.append('```xl')
        width = max(len(k) for k, v in lines)
        for line in lines:
            message.append('{0:<{width}} : {1}'.format(*line, width=width))
        message.append('```')

        await self.bot.say('\n'.join(message))

    @overwatch.command(pass_context=True)
    async def heroes(self, ctx, tag: player_tag = '', tier=None):
        """Get stats for each played hero.

        [tag] can be either BattleTag or a mention to someone in the db
        [tier] can be 'quick', 'quickplay', 'qp', 'comp', or 'competitive'
             * Defaults to competitive stats, falls back to quickplay.
        """
        try:
            _, heroes, tag, tier = await self.get_all(ctx, tag, tier, HEROES)
        except NotInDB:
            await self.bot.say("Not in the db.")
            return

        message = ['{} hero stats:'.format(tier.title())]
        width = max(len(k) for k in heroes.keys())
        message.append('```xl')
        for hero, time in sorted(heroes.items(), key=lambda kv: kv[1],
                                 reverse=True):
            if time:
                message.append('{0:<{width}} : {1}'.format(
                    hero.title(),
                    time_str(heroes[hero]),
                    width=width))
        message.append('```')
        await self.bot.say('\n'.join(message))

    @overwatch.command(name='set', aliases=['save'], pass_context=True)
    async def ow_set(self, ctx, tag, tier=None):
        """Set your battletag and default tier.

        <tag> can be either BattleTag or a mention to someone in the db
        [tier] can be 'quick', 'quickplay', 'qp', 'comp', or 'competitive'
             * Defaults to competitive stats, falls back to quickplay.
        """
        author_id = ctx.message.author.id
        in_db = bool(await self.bot.db.fetchval('''
            SELECT id FROM overwatch WHERE id = $1
            ''', author_id))
        if in_db and tier is None and tag in TIERS:
            tag, tier, _ = await self.get_tag_tier(ctx, tag, tier)
        else:
            tag = tag[::-1].replace('#', '-', 1)[::-1]
            tier = ow_tier(tier)
        async with self.bot.db.transaction():
            if in_db:
                await self.bot.db.execute('''
                    UPDATE overwatch SET tier = $1 WHERE id = $2
                    ''', tier, author_id)
                message = '\N{THUMBS UP SIGN} Updated preference.'
            else:
                await self.bot.db.execute('''
                    INSERT INTO overwatch (id, btag, tier) VALUES ($1, $2, $3)
                    ''', author_id, tag, tier)
                message = '\N{THUMBS UP SIGN} Added to db.'
        await self.bot.say(message)


def setup(bot):
    bot.add_cog(Overwatch(bot))
