"""The contents of this cog is taken entirely from Rapptz RoboDanny bot. Don't sue me.""" 
from contextlib import redirect_stdout
from datetime import datetime
import traceback
import inspect
import io

from discord.ext import commands
import discord

from .utils import checks


def date(argument):
    formats = (
        '%Y/%m/%d',
        '%Y-%m-%d',
    )

    for fmt in formats:
        try:
            return datetime.strptime(argument, fmt)
        except ValueError:
            continue

    raise commands.BadArgument('Cannot convert to date. Expected YYYY/MM/DD or YYYY-MM-DD.')


class RoboDanny:
    def __init__(self, bot):
        self.bot = bot
        self.sessions = set()
        self.last_eval = None

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def repl(self, ctx):
        msg = ctx.message

        variables = {
            'discord': discord,
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author,
            'me': msg.author,
            '__': None
        }

        if msg.channel.id in self.sessions:
            await self.bot.say('Already running a REPL session in this channel. Exit it with `quit`.')
            return

        self.sessions.add(msg.channel.id)
        await self.bot.say('Enter code to execute or evaluate. `exit()` or `quit` to exit.')
        while True:
            response = await self.bot.wait_for_message(author=msg.author, channel=msg.channel,
                                                       check=lambda m: m.content.startswith('`'))

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await self.bot.say('Exiting.')
                self.sessions.remove(msg.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await self.bot.say(self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = '```py\n{}{}\n```'.format(value, traceback.format_exc())
            else:
                value = stdout.getvalue()
                variables['__'] = result
                if result is not None:
                    fmt = '```py\n{}{}\n```'.format(value, result)
                    variables['last'] = result
                elif value:
                    fmt = '```py\n{}\n```'.format(value)

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await self.bot.send_message(msg.channel, 'Content too big to be printed.')
                    else:
                        await self.bot.send_message(msg.channel, fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await self.bot.send_message(msg.channel, 'Unexpected error: `{}`'.format(e))

    @commands.command(pass_context=True, hidden=True, aliases=['eval'])
    @checks.is_owner()
    async def debug(self, ctx, *, code : str):
        """Evaluates code."""
        msg = ctx.message
        code = code.strip('` ')
        python = '```py\n{}\n```'
        result = None

        env = {
            'discord': discord,
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author,
            'me': msg.author,
            '__': self.last_eval
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await self.bot.say(python.format(type(e).__name__ + ': ' + str(e)))
            return
        self.last_eval = result
        await self.bot.say(python.format(result))

    @commands.command(pass_context=True)
    @commands.has_permissions(manage_messages=True)
    async def nostalgia(self, ctx, date: date = None, *, channel: discord.Channel = None):
        """Pins an old message from a specific date.

        If a date is not given, then pins first message from the channel.
        If a channel is not given, then pins from the channel the
        command was ran on.

        The format of the date must be either YYYY-MM-DD or YYYY/MM/DD.
        """

        if channel is None:
            channel = ctx.message.channel
        if date is None:
            date = channel.created_at

        async for m in self.bot.logs_from(channel, after=date, limit=1):
            try:
                await self.bot.pin_message(m)
            except:
                await self.bot.say('\N{THUMBS DOWN SIGN} Could not pin message.')

    @nostalgia.error
    async def nostalgia_error(self, error, ctx):
        if isinstance(error, commands.BadArgument):
            await self.bot.say(error)


def setup(bot):
    bot.add_cog(RoboDanny(bot))
