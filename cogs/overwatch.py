import json
import os
import re

from discord.ext import commands
import aiohttp

from .utils import utils

ow_storage = os.path.join(os.path.split(os.path.split(__file__)[0])[0],
                          'ow.dat')
if not os.path.exists(ow_storage):
    with open(ow_storage, 'w') as fp:
        fp.write('{}')

endpoint = "https://owapi.net/api/v2/u/{{tag}}/{cat}/{{tier}}"
stat_endpoint = endpoint.format(cat='stats')
hero_endpoint = endpoint.format(cat='heroes')

tiers = ('quick', 'quickplay', 'qp', 'general', 'unranked',
         'comp', 'competitive', 'ranked')


class Not200(Exception):
    pass


def player_tag(arg):
    match = re.match(r'<@!?([0-9]+)>$', arg)
    if match is not None:
        return match.group(1)
    else:
        return arg[::-1].replace('#', '-', 1)[::-1]


def ow_tier(arg):
    if arg in tiers[:5]:
        return 'general'
    return 'competitive'


def ow_level(overall_stats):
    total = overall_stats['prestige'] * 100
    total += overall_stats['level']
    return total


def time_from_decimal(dec):
    return divmod(round(dec * 60), 60)


def most_played(hero_dict):
    mp_time = max(hero_dict.values())
    for hero, played in hero_dict.items():
        if played == mp_time:
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
        with open(ow_storage) as fp:
            self.idents = json.load(fp)

    async def fetch_stats(self, tag, tier, it=0):
        if it == 2:
            raise RecursionError
        with aiohttp.Timeout(10):
            async with self.bot.aiohsession.get(
                    stat_endpoint.format(tag=tag, tier=tier)) as resp:
                s1, j1 = resp.status, await resp.json()
            async with self.bot.aiohsession.get(
                    hero_endpoint.format(tag=tag, tier=tier)) as resp:
                s2, j2 = resp.status, await resp.json()
        if tier == 'competitive' and (s1 != 200 or s2 != 200):
            try:
                j1['msg']
            except:
                raise Not200
            else:
                j1, j2, tier = await self.fetch_stats(tag, 'general', it + 1)
        return j1, j2, tier

    def get_tag(self, ctx, tag):
        member_id = None
        tag = player_tag(tag)
        if tag == '' or '-' not in tag:
            member_id = tag or ctx.message.author.id
            tag = self.idents[member_id]['btag']
        return tag, member_id

    def get_tier(self, member_id):
        return self.idents[member_id]['tier']

    def get_tag_tier(self, ctx, tag, tier):
        if tag in tiers:
            tier = ow_tier(tag)
            tag, member_id = self.get_tag(ctx, '')
        else:
            tag, member_id = self.get_tag(ctx, tag)
            if tier is not None:
                tier = ow_tier(tier)
            else:
                try:
                    tier = self.get_tier(member_id)
                except KeyError:
                    tier = 'competitive'
        return tag, tier, member_id

    async def get_all(self, ctx, tag, tier):
        tag, tier, member_id = self.get_tag_tier(ctx, tag, tier)
        stats, heroes, tier = await self.fetch_stats(tag, tier)
        heroes = heroes['heroes']
        if tier == 'general':
            tier = 'quickplay'
        return stats, heroes, tag, tier

    @commands.group(aliases=['ow'], pass_context=True,
                    invoke_without_command=True)
    async def overwatch(self, ctx, tag: player_tag = '', tier=None):
        """See stats of yourself or another player.

        [tag] can be either BattleTag or a mention to someone in the db
        [tier] can be 'quick', 'quickplay', 'qp', 'unranked',
                      'comp', 'competitive', 'ranked'
             * Defaults to competitive stats, falls back to quickplay.

        Stats by Battletag       : !ow BattleTag#1234
        Stats by Discord mention : !ow @DiscordName
        Add yourself to database : !ow set BattleTag#1234
        Hero Play Time           : !ow heroes BattleTag#1234

        Notes
            * You can follow BattleTag/Discord mention with a tier of gameplay
                to force getting quickplay/competitive stats.
            * BattleTags are case-sensitive.
            * To get stats by Discord mention, the person must be in the DB.
        """
        try:
            stats, heroes, tag, tier = await self.get_all(ctx, tag, tier)
        except KeyError:
            await self.bot.say("Not in the db.")
            return

        mp_hero, mp_time = most_played(heroes)

        message = ['{} stats:'.format(tier.title())]
        lines = [
            ('Battletag', stats['battletag'][::-1].replace('-', '#', 1)[::-1]),
            ('Time played', time_str(stats['game_stats']['time_played'])),
            ('Level', ow_level(stats['overall_stats'])),
            ('Competitive Rank', stats['overall_stats']['comprank'] or
             'Unranked'),
            ('Most Played Hero', mp_hero),
            ('Hero Time', time_str(mp_time)),
            ('Games Played', stats['overall_stats']['games']),
            ('Games Won', stats['overall_stats']['wins']),
            ('Win Rate', '{}%'.format(stats['overall_stats']['win_rate'])),
            ('Kill/death', round(stats['game_stats']['kpd'], 2))]
        try:
            lines.append(('Environmental Deaths',
                          int(stats['game_stats']['environmental_deaths'])))
        except:
            pass
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
            stats, heroes, tag, tier = await self.get_all(ctx, tag, tier)
        except KeyError:
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
        if tier is None and tag in tiers:
            tag, tier, _ = self.get_tag_tier(ctx, tag, tier)
            try:
                tag = self.idents[ctx.message.author.id]['btag']
            except:
                await self.bot.say("You're not in the db.")
                return
        else:
            tier = ow_tier(tier)
            tag = tag[::-1].replace('#', '-', 1)[::-1]
        self.idents[ctx.message.author.id] = {'btag': tag, 'tier': tier}
        with open(ow_storage, 'w') as fp:
            json.dump(self.idents, fp)
        await self.bot.say('\N{OK HAND SIGN} Added to db.')


def setup(bot):
    bot.add_cog(Overwatch(bot))
