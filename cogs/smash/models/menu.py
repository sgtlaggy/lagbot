import random

from discord.ext import menus
import discord


class FighterPageSource(menus.ListPageSource):
    @staticmethod
    def format_name(fighter):
        if fighter.aliases:
            return f'{fighter.name} ({", ".join(fighter.aliases)})'
        else:
            return fighter.name

    async def format_page(self, menu, entries):
        random_fighter = random.choice(entries)
        embed = discord.Embed(title='Fighters', color=random_fighter.color)
        fighters = '\n'.join(f'{f.number}. {self.format_name(f)}' for f in entries)
        latest = self.entries[-1]
        embed.description = f'Latest fighter: {self.format_name(latest)}\n\n{fighters}'
        embed.set_footer(text=f'Page {menu.current_page + 1}/{self.get_max_pages()}')
        return embed


class FighterMenu(menus.MenuPages):
    async def start(self, ctx, *args, users=None, **kwargs):
        owner_ids = {ctx.bot.owner_id, *ctx.bot.owner_ids}
        self.users = (set(u.id for u in users) if users else {ctx.author.id}) | owner_ids
        await super().start(ctx, *args, **kwargs)

    def reaction_check(self, payload):
        if payload.message_id != self.message.id:
            return False
        if payload.user_id not in self.users:
            return False
        return payload.emoji in self.buttons

    @menus.button('\N{TIMER CLOCK}\ufe0f', position=menus.Last(3))
    async def extend_timeout(self, payload):
        """Reset timeout."""
        pass
