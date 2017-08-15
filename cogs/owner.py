"""The eval commands are from Rapptz's RoboDanny. Don't sue me."""
from contextlib import redirect_stdout
from timeit import timeit
from dis import dis
import traceback
import textwrap
import asyncio
import inspect
import io

from discord.ext import commands
import discord

from utils.utils import UPPER_PATH, send_error
from utils.checks import need_db
from utils import checks


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


def get_env(ctx):
    return dict(
        print=print_,
        timeit=timeit,
        dis=dis,
        discord=discord,
        bot=ctx.bot,
        client=ctx.bot,
        ctx=ctx,
        con=ctx.con,
        msg=ctx.message,
        message=ctx.message,
        guild=ctx.guild,
        server=ctx.guild,
        channel=ctx.channel,
        me=ctx.me
    )


class Owner:
    """Commands I stole from Robodanny (https://github.com/Rapptz/RoboDanny)."""
    def __init__(self, bot):
        self.bot = bot
        self.last_eval = None

    def eval_output(self, out=None):
        lines = []
        if out is not None:
            if out.startswith('\n'):
                out = "''" + out
            lines.append(out if out != '' else "''")
        if lines:
            out = '```py\n' + '\n'.join(lines) + '\n```'
            if len(out) > 2000:
                out = '```py\nOutput too long.\n```'
            return out
        else:
            return

    async def __local_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command(aliases=['restart', 'kill'], hidden=True)
    async def exit(self, ctx, code: int = None):
        """Restart/kill the bot.

        Optionally set exit code for custom handling.
        """
        codes = {'restart': 2, 'kill': 1}
        code = codes.get(ctx.invoked_with, code)
        if code is None:
            return await ctx.send('Invalid exit code.')
        self.bot.exit_status = code
        await self.bot.logout()

    @need_db
    @commands.command(hidden=True, name='eval')
    async def eval_(self, ctx, *, code: cleanup_code):
        """Alternative to `debug` that executes code inside a coroutine.

        Allows multiple lines and `await`ing.

        This is a modified version of RoboDanny's latest `eval` command.
        """
        env = get_env(ctx)

        to_compile = 'async def _func():\n%s' % textwrap.indent(code, '  ')

        stdout = io.StringIO()
        try:
            exec(to_compile, env)
        except SyntaxError as e:
            return await ctx.send(self.eval_output('\n'.join(get_syntax_error(e).splitlines()[1:-1])))

        func = env['_func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            exc = traceback.format_exc().replace(UPPER_PATH, '...').splitlines()
            exc = '\n'.join([exc[0], *exc[3:]])
            await ctx.send(self.eval_output(f'{value}{exc}'))
        else:
            value = stdout.getvalue()
            if isinstance(ret, discord.Embed):
                await ctx.send(self.eval_output(value if value else None), embed=ret)
            else:
                await ctx.send(self.eval_output(value if ret is None else f'{value}{rep(ret)}'))

    @need_db
    @commands.command(hidden=True, aliases=['py'])
    async def debug(self, ctx, *, code: cleanup_code):
        """Evaluates code."""
        result = None
        env = get_env(ctx)
        env['__'] = self.last_eval

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, discord.Embed):
                return await ctx.send(embed=result)
        except Exception as e:
            say = self.eval_output(exception_signature())
        else:
            say = self.eval_output(rep(result))
        if say is None:
            say = 'None'
        await ctx.send(say)


def setup(bot):
    bot.add_cog(Owner(bot))
