"""The eval commands are from Rapptz's RoboDanny. Don't sue me."""
from contextlib import redirect_stdout
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


class Owner:
    """Commands I stole from Robodanny (https://github.com/Rapptz/RoboDanny)."""
    def __init__(self, bot):
        self.bot = bot
        self.last_eval = None
        if not hasattr(bot, 'errors'):
            bot.errors = {}

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

    @need_db
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
            'con': ctx.con,
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
            await ctx.send(self.eval_output('\n'.join(get_syntax_error(e).splitlines()[1:-1])))
            return

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
    @commands.is_owner()
    async def debug(self, ctx, *, code: cleanup_code):
        """Evaluates code."""
        msg = ctx.message

        result = None
        env = {
            'discord': discord,
            'print': print_,
            'ctx': ctx,
            'con': ctx.con,
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
            say = self.eval_output(exception_signature())
        else:
            say = self.eval_output(rep(result))
        if say is None:
            say = 'None'
        await ctx.send(say)

    @commands.command(hidden=True, aliases=['edm'])
    @commands.is_owner()
    @checks.dm_only()
    async def etell(self, ctx, num: int, *, content):
        """Respond to an error that occured."""
        try:
            error_ctx = self.bot.errors[num]
        except KeyError:
            await ctx.send(f'There is no error #{num}.')
            return
        dest = error_ctx.channel if ctx.invoked_with == 'tell' else await error_ctx.author.create_dm()
        await dest.send(content)
        try:
            r = await self.bot.wait_for('message', timeout=60,
                                        check=lambda m: m.channel == dest and m.author == error_ctx.author)
        except asyncio.TimeoutError:
            pass
        else:
            await ctx.send(f'{num} {r.content}')

    @commands.command(hidden=True)
    @commands.is_owner()
    @checks.dm_only()
    async def eshow(self, ctx, num: int = None):
        if num:
            try:
                error_ctx = self.bot.errors[num]
            except KeyError:
                await ctx.send(f'There is no error #{num}.')
            else:
                await send_error(ctx, error_ctx, error_ctx.error, num)
        else:
            await ctx.send(' '.join(str(k) for k in self.bot.errors.keys()))

    @commands.command(hidden=True)
    @commands.is_owner()
    @checks.dm_only()
    async def eclose(self, ctx, num: int):
        try:
            self.bot.errors.pop(num)
        except KeyError:
            await ctx.send(f'There is no error #{num}.')
        else:
            await ctx.send(f'Closed error #{num}.')

    @commands.command(hidden=True)
    @commands.is_owner()
    @checks.dm_only()
    async def eclear(self, ctx):
        self.bot.errors = {}
        await ctx.send('Cleared all errors.')

    async def on_command_error(self, ctx, exc):
        if hasattr(ctx.command, 'on_error') or getattr(exc, 'handled', False) or \
                not isinstance(exc, commands.CommandInvokeError) or isinstance(exc.original, discord.Forbidden):
            return
        error_num = max(self.bot.errors or (0,)) + 1
        ctx.error = exc.original
        self.bot.errors[error_num] = ctx


def setup(bot):
    bot.add_cog(Owner(bot))
