"""Most of the contents are from Rapptz RoboDanny bot. Don't sue me."""
from contextlib import redirect_stdout
from datetime import datetime
import traceback
import textwrap
import inspect
import io

from discord.ext import commands
import discord


def date(argument):
    formats = ('%Y/%m/%d', '%Y-%m-%d')
    for fmt in formats:
        try:
            return datetime.strptime(argument, fmt)
        except ValueError:
            continue
    raise commands.BadArgument('Cannot convert to date. Expected YYYY/MM/DD or YYYY-MM-DD.')


def exception_signature():
    return traceback.format_exc().split('\n')[-2]


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def get_syntax_error(e):
    return f'```py\n{e.text}{"^":>{e.offset}}\n{type(e).__name__}: {e}\n```'


def rep(obj):
    return repr(obj) if isinstance(obj, str) else str(obj)


def print_(*args, **kwargs):
    new_args = [rep(arg) for arg in args]
    print(*new_args, **kwargs)


class RoboDanny:
    """Commands I stole from Robodanny (https://github.com/Rapptz/RoboDanny)."""
    def __init__(self, bot):
        self.bot = bot
        self.last_eval = None

    async def eval_output(self, out=None):
        lines = []
        if out is not None:
            link = await self.maybe_upload(out, len('```py\n' + '\n'.join(lines) + '\n\n```'))
            if link.startswith('\n'):
                link = "''" + link
            lines.append(link if link != '' else "''")
        if lines:
            return '```py\n' + '\n'.join(lines) + '\n```'
        else:
            return

    async def maybe_upload(self, content, cur_len=0, max_len=2000):
        """Checks length of content and returns either the content or link to paste."""
        contents = str(content)
        if len(contents) >= 2 and contents[-2] == '\n':
            contents = contents[:-2] + contents[-1]
        if len(contents) <= max_len - cur_len:
            return contents
        resp = await self.bot.request('https://hastebin.com/documents', data=contents, type_='text')
        if resp.status == 201:
            return f'https://hastebin.com/{resp.data}'
        return 'Result too long and error occurred while posting to hastebin.'

    @commands.command(hidden=True, name='eval')
    @commands.is_owner()
    async def eval_(self, ctx, *, code: cleanup_code):
        """Alternative to `debug` that executes code inside a coroutine.

        Allows multiple lines and `await`ing.

        This is a modified version of RoboDanny's latest `eval` command.
        """
        msg = ctx.message

        env = {
            'discord': discord,
            'print': print_,
            'bot': self.bot,
            'client': self.bot,
            'ctx': ctx,
            'msg': msg,
            'message': msg,
            'guild': msg.guild,
            'server': msg.guild,
            'channel': msg.channel,
            'me': msg.author
        }

        to_compile = 'async def _func():\n%s' % textwrap.indent(code, '  ')

        stdout = io.StringIO()
        try:
            exec(to_compile, env)
        except SyntaxError as e:
            await ctx.send(await self.eval_output('\n'.join(get_syntax_error(e).splitlines()[1:-1])))
            return

        func = env['_func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            exc = traceback.format_exc().splitlines()
            exc = '\n'.join([exc[0], *exc[3:]])
            await ctx.send(await self.eval_output(f'{value}{exc}'))
        else:
            value = stdout.getvalue()
            if isinstance(ret, discord.Embed):
                await ctx.send(await self.eval_output(value if value else None), embed=ret)
            else:
                await ctx.send(await self.eval_output(value if ret is None else f'{value}{rep(ret)}'))

    @commands.command(hidden=True, aliases=['py'])
    @commands.is_owner()
    async def debug(self, ctx, *, code: cleanup_code):
        """Evaluates code."""
        msg = ctx.message

        result = None
        env = {
            'discord': discord,
            'print': print_,
            'ctx': ctx,
            'bot': self.bot,
            'client': self.bot,
            'message': msg,
            'msg': msg,
            'guild': msg.guild,
            'server': msg.guild,
            'channel': msg.channel,
            'author': msg.author,
            'me': msg.author,
            '__': self.last_eval
        }

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, discord.Embed):
                await ctx.send(embed=result)
                return
        except Exception as e:
            say = await self.eval_output(exception_signature())
        else:
            say = await self.eval_output(rep(result))
        if say is None:
            say = 'None'
        await ctx.send(say)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def nostalgia(self, ctx, date: date = None, *, channel: discord.TextChannel = None):
        """Pins an old message from a specific date.

        If a date is not given, then pins first message from the channel.
        If a channel is not given, then pins from the channel the
        command was ran on.

        The format of the date must be either YYYY-MM-DD or YYYY/MM/DD.
        """

        if channel is None:
            channel = ctx.channel
        if date is None:
            date = channel.created_at

        async for m in ctx.history(after=date, limit=1):
            try:
                await m.pin()
            except:
                await ctx.send('\N{THUMBS DOWN SIGN} Could not pin message.')

    @nostalgia.error
    async def nostalgia_error(self, error, ctx):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)


def setup(bot):
    bot.add_cog(RoboDanny(bot))
