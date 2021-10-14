import random

from discord import ui, Interaction, Embed
from discord.ext import menus


class FighterPageSource(menus.ListPageSource):
    @staticmethod
    def format_name(fighter):
        if fighter.aliases:
            return f'{fighter.name} ({", ".join(fighter.aliases)})'
        else:
            return fighter.name

    async def format_page(self, menu, entries):
        random_fighter = random.choice(entries)
        embed = Embed(title='Fighters', color=random_fighter.color)
        fighters = '\n'.join(f'{f.number}. {self.format_name(f)}' for f in entries)
        latest = self.entries[-1]
        embed.description = f'Latest fighter: {self.format_name(latest)}\n\n{fighters}'
        embed.set_footer(text=f'Page {menu.current_page + 1}/{self.get_max_pages()}')
        return embed


class FighterMenu(ui.View, menus.MenuPages):
    def __init__(self, source):
        super().__init__()
        self._source = source
        self.current_page = 0
        self.update_buttons()
        self.ctx = None
        self.message = None

    async def start(self, ctx, *args, **kwargs):
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        value = await super()._get_kwargs_from_page(page)
        value['view'] = self
        return value

    async def interaction_check(self, itx: Interaction):
        return itx.user == self.ctx.author

    def update_buttons(self):
        for child in self.children:
            child.disabled = False
        if self.current_page == 0:
            self.first_page.disabled = True
            self.prev_page.disabled = True
        elif self.current_page == (self._source.get_max_pages() - 1):
            self.next_page.disabled = True
            self.last_page.disabled = True

    @ui.button(emoji='\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f')
    async def first_page(self, btn: ui.Button, itx: Interaction):
        self.current_page = 0
        self.update_buttons()
        await self.show_current_page()

    @ui.button(emoji='\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f')
    async def prev_page(self, btn: ui.Button, itx: Interaction):
        self.current_page -= 1
        self.update_buttons()
        await self.show_current_page()

    @ui.button(emoji='\N{BLACK SQUARE FOR STOP}\ufe0f')
    async def stop_view(self, btn: ui.Button, itx: Interaction):
        self.stop()
        await self.message.delete(delay=0)  # silently ignore failure

    @ui.button(emoji='\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f')
    async def next_page(self, btn: ui.Button, itx: Interaction):
        self.current_page += 1
        self.update_buttons()
        await self.show_current_page()

    @ui.button(emoji='\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f')
    async def last_page(self, btn: ui.Button, itx: Interaction):
        self.current_page = (self._source.get_max_pages() - 1)
        self.update_buttons()
        await self.show_current_page()