"""Cog for stream stuff."""

from discord.ext import commands
import asyncio
import json
import os

from .utils import *


class Stream:
    """Stream command stuff."""

    def __init__(self, bot):
        """Constructor."""
        self.bot = bot

        self.stream_file = os.path.join(
            *os.path.split(
                os.path.abspath(__file__))[0].split('\\')[:-1],
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
        {0}stream link                   (announce someone not in discord)
        {0}stream @user                  (announce someone else)
        {0}stream                        (announce yourself)
        {0}stream # announcement message (announce message, mention everyone)
        {0}stream $ announcement message (announce message, no mention)
        {0}stream add @user link         (add someone to list)
        {0}stream rem @user              (remove someone from list)
        """
        if ctx.invoked_subcommand is None:
            stream_text = '{} is streaming at {}'
            msg = ctx.message
            message = stream_message(args)
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
        """Add or update a streamer's link.

        Usage:
        {0}stream add @user link
        """
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
        """Remove streamer from list.

        Usage:
        {0}stream rem @user
        """
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
    """'Magic' function to set up cog."""
    bot.add_cog(Stream(bot))
