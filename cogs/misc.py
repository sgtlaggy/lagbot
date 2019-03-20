from collections import OrderedDict
import unicodedata
import datetime
import random
import string

from discord.ext import commands
import discord

from utils.utils import integer, pluralize
from cogs.base import BaseCog
from utils import dice


_all_chars = string.punctuation + string.digits + string.ascii_letters
_chars = {c: ord(c) + 65248 for c in _all_chars}
_chars[' '] = ord(' ') + 12256
FW_TRANS = str.maketrans(_chars)


def fancy_time(orig_time, utc=False):
    diff = datetime.datetime.utcnow() - orig_time
    nice = ''
    if diff.days >= 365:
        years = diff.days // 365
        nice += pluralize('year', 'years', years, "{n} {s}, ")
    days = diff.days % 365
    nice += pluralize('day', 'days', days, "{n} {s} ago")
    if utc:
        nice += f' ({orig_time} UTC)'
    else:
        nice += f' ({orig_time:%Y-%m-%d})'
    return nice


def die(arg):
    return (arg, dice.roll(arg))


def hex_or_rgb(arg):
    s = arg.split(' ')
    if len(s) == 1:
        color = s[0]
        if len(color) == 6:
            color = f'0x{color}'
        elif len(color) == 7:
            color = color.replace('#', '0x')
        try:
            return discord.Color(int(color, 0))
        except ValueError:
            raise commands.BadArgument('A single argument must be passed as hex (`0x7289DA`, `#7289DA`, `7289DA`)')
    elif len(s) == 3:
        try:
            rgb = [*map(int, s)]
        except ValueError:
            raise commands.BadArgument('Three arguments must be passed as RGB (`114 137 218`, `153 170 181`)')
        if any(c < 0 or c > 255 for c in rgb):
            raise commands.BadArgument('RGB colors must be in the range `[0, 255]`')
        return discord.Color.from_rgb(*rgb)
    raise commands.BadArgument('You must pass 1 (hex) or 3 (RGB) arguments.')


class Misc(BaseCog):
    """Miscellaneous commands that don't fit in other categories."""
    @commands.command(name='roll')
    async def roll_dice(self, ctx, *rolls: die):
        """In format CdS, rolls C dice each with S sides.

        If C is neglected, it will be assumed to mean 1 die.

        Advanced notation:
            * add "^X" to keep the highest X rolls          : 10d6^3 -> 4, 4, 5
            * add "vX" to keep the lowest X rolls           : 10d6v3 -> 1, 2, 2
            * add "x" to explode when rolling highest value : 1d6x -> 6, 3
            * add "t" to get the total of the rolls         : 2d6t   -> 9
            * add "s" to sort the rolls                     : 2d6s   -> 2, 4

        ^ and v are mutually exclusive.
        t and s are mutually exclusive.

        You can also specify a list of dice to roll. "1d6 2d20 d12"
        """
        rolls = rolls or [('1d6', random.randint(1, 6))]
        msg = []
        for roll, result in rolls:
            if isinstance(result, list):
                result = ', '.join(map(str, result))
            msg.append(f'{roll}: {result}')
        await ctx.send('\n'.join(msg))

    @roll_dice.error
    async def roll_error(self, ctx, exc):
        if isinstance(exc, commands.BadArgument):
            await ctx.send(str(exc.__cause__))

    @commands.command()
    async def flip(self, ctx, coins: integer = 1):
        """Flip any number of coins."""
        coins = coins if coins >= 1 else 1
        flips = OrderedDict([('Heads', 0), ('Tails', 0), ('Edge', 0)])

        for _ in range(coins):
            rand = random.randint(0, 6000)
            if rand:
                if rand % 2:
                    flips['Heads'] += 1
                else:
                    flips['Tails'] += 1
            else:  # 1/6001 chance of being edge
                flips['Edge'] += 1

        message = []
        for f, c in flips.items():
            if c:
                if coins == 1:
                    message.append(f)
                    break
                message.append(f'{f}: {c}')
        message = '\n'.join(message)
        await ctx.send(message)

    @commands.command()
    async def choose(self, ctx, *options):
        """Choose a random element from a list of items.

        Any item that contains a space must be wrapped in double quotes (").
        """
        if len(options) == 0:
            await ctx.send('No.')
        else:
            await ctx.send(random.choice(options))

    @commands.command()
    @commands.guild_only()
    async def info(self, ctx, *, member: discord.Member = None):
        """Display information of specific user."""
        member = member or ctx.author
        roles = [f'@{role}' for role in member.roles if role.name != '@everyone']
        embed = discord.Embed(colour=member.colour)
        embed.add_field(name='Name', value=member.name)
        embed.add_field(name='Tag', value=member.discriminator)
        embed.add_field(name='ID', value=member.id)
        embed.add_field(name='Joined Server', value=fancy_time(member.joined_at)[::-1].replace(' ', '\n', 1)[::-1])
        embed.add_field(name='Joined Discord', value=fancy_time(member.created_at)[::-1].replace(' ', '\n', 1)[::-1])
        embed.add_field(name='Roles', value=' '.join(roles) or 'None')
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def charinfo(self, ctx, *, chars):
        """Get unicode character info."""
        if not chars:
            return
        chars = unicodedata.normalize('NFC', chars)
        if len(chars) > 25:
            await ctx.send('Too many emoji.')
            return
        embed = discord.Embed()
        for char in chars:
            uc = hex(ord(char))[2:]
            name = unicodedata.name(char, 'unknown')
            if name in {'SPACE', 'EM QUAD', 'EN QUAD'} or ' SPACE' in name:
                char = '" "'
            short = len(uc) <= 4
            code = f'`\\{"u" if short else "U"}{uc.lower().zfill(4 if short else 8)}`'
            embed.add_field(name=name,
                            value=f'{char} [{code}](http://www.fileformat.info/info/unicode/char/{uc}/index.htm)')
        await ctx.send(embed=embed)

    @commands.command(aliases=['fw'])
    async def fullwidth(self, ctx, *, chars):
        """Turn your lame normal text into full-width text."""
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send(chars.translate(FW_TRANS))

    @commands.command(usage='<rgb/hex>')
    async def color(self, ctx, *, color: hex_or_rgb):
        """See hex or RGB color.

        <rgb/hex> can be provided as any of the following:
        0x7289DA
        #7289DA
        7289DA
        114 137 218
        """
        em = discord.Embed(color=color, description=f'Hex: {color}\nRGB: {color.to_rgb()}')
        await ctx.send(embed=em)

    @color.error
    async def color_error(self, ctx, exc):
        if isinstance(exc, commands.BadArgument):
            await ctx.send(exc)


def setup(bot):
    bot.add_cog(Misc(bot))
