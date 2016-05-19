from discord.ext import commands
import asyncio
import json
import os


def is_url(text):
    """Check if a string is a standard http(s) URL."""
    if text.startswith('http:') or text.startswith('https:'):
        return True
    return False


def stream_name_link(nl):
    """Get stream link from name or vice-versa."""
    if is_url(nl):
        link = nl
        name = link.split('/')[-1]
    else:
        name = nl
        link = 'http://twitch.tv/{}'.format(name.lower())
    return name, link


def stream_message(*args):
    """Get message in stream announcement."""
    message = ''
    if '#' in args:
        for i, a in enumerate(args):
            if a == '#':
                message = '@here ' + ' '.join(args[i + 1:])
                break
    elif '$' in args:
        for i, a in enumerate(args):
            if a == '$':
                message = ' '.join(args[i + 1:])
                break
    if message:
        message += '\n'
    return message


class Stream:
    """Stream command stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot

        # wrapped in os.path.split()[0] twice for windows compatibility because
        # .join just doesn't work properly
        self.stream_file = os.path.join(
            os.path.split(os.path.split(os.path.abspath(__file__))[0])[0],
            'data', 'stream.json')
        try:
            with open(self.stream_file, 'r') as fp:
                self.streamers = json.load(fp)
        except:
            self.streamers = {}

    @commands.group(pass_context=True, invoke_without_command=True)
    async def stream(self, ctx, *args):
        """Announce that you or someone else is streaming.

        Usage:
        {prefix}stream link                   (announce someone not in discord)
        {prefix}stream @user                  (announce someone else)
        {prefix}stream                        (announce yourself)
        {prefix}stream # announcement message (announce message, mention everyone)
        {prefix}stream $ announcement message (announce message, no mention)
        {prefix}stream add @user link         (add someone to list)
        {prefix}stream rem @user              (remove someone from list)
        """
        if ctx.invoked_subcommand is None:
            stream_text = '{} is streaming at {}'
            msg = ctx.message
            message = stream_message(*args)
            message += stream_text
            if len(args) == 0 or args[0] in ('#', '$'):
                try:
                    author = msg.author
                    link = self.streamers[author.id]
                    await self.bot.say(message.format(author.name, link))
                except KeyError:
                    await self.bot.say('You are not in the list of streamers.')
            elif len(msg.mentions) == 0:
                name, link = stream_name_link(args[0])
                await self.bot.say(message.format(name, link))
            else:
                for m in msg.mentions:
                    try:
                        await self.bot.say(message.format(
                            m.name, self.streamers[m.id]))
                    except:
                        await self.bot.say(
                            '{} is not in the list of streamers.'.format(
                                m.name))
            try:
                await self.bot.delete_message(msg)
            except:
                pass

    @stream.command(name='add', pass_context=True)
    async def add_stream(self, ctx, _, link):
        """Add or update a streamer's link."""
        member = ctx.message.mentions[0]
        try:
            name, link = member.name, link
            sid = member.id
        except:
            return
        self.streamers[sid] = link
        with open(self.stream_file, 'w') as s:
            json.dump(self.streamers, s)
        await self.bot.say('Added {} ({}) to steamer list.'.format(name, link))

    @stream.command(name='remove', aliases=['rem'], pass_context=True)
    async def remove_stream(self, ctx, _):
        """Remove streamer from list."""
        member = ctx.message.mentions[0]
        try:
            name, sid = member.name, member.id
        except:
            return
        try:
            del self.streamers[sid]
        except:
            return
        with open(self.stream_file, 'w') as s:
            json.dump(self.streamers, s)
        await self.bot.say('{} has been removed.'.format(name))


def setup(bot):
    """Magic function to set up cog."""
    bot.add_cog(Stream(bot))
