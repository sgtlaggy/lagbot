from __future__ import annotations
from typing import Coroutine, Optional, Union
from datetime import datetime

from discord import ui, Interaction, SelectOption, ButtonStyle, Embed, Color
from discord.ext.commands import Cog, Command, Group, DefaultHelpCommand


BotMapping = dict[Optional[Cog], list[Command]]
Entity = Optional[Union[Cog, Command]]


class ComponentHelp(DefaultHelpCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mapping = None
        self._embed = Embed(color=self.color, timestamp=datetime.now().astimezone())

    @property
    def embed(self):
        return self._embed.copy() \
            .set_footer(icon_url=self.context.author.avatar.url,  # update footer if user changes name/avatar
                        text=f'For @{self.context.author} at')

    @staticmethod
    def enumerate_commands(commands: list[Command]):
        for command in commands:
            yield f'`{command}` - {command.brief}'

    async def get_filtered_mapping(self) -> BotMapping:
        if self._mapping is None:
            mapping = {cog: await self.filter_commands(cmds)
                   for cog, cmds in self.get_bot_mapping().items()}
            # filter out cogs with no commands post-filter
            self._mapping = {cog: cmds for cog, cmds in mapping.items() if cmds}
        return self._mapping

    async def send_view(self, embed: Embed, entity: Entity):
        mapping = await self.get_filtered_mapping()
        view = HelpView(self, mapping, entity)
        await view.update_commands()  # must be async to filter subcommands
        view.message = await self.get_destination().send(embed=embed, view=view)

    async def send_bot_help(self, mapping: BotMapping):
        mapping = await self.get_filtered_mapping()
        embed = await self.get_bot_help(mapping)
        await self.send_view(embed, None)

    async def send_cog_help(self, cog: Cog):
        mapping = await self.get_filtered_mapping()
        if cog not in mapping:
            return

        embed = await self.get_cog_help(cog)
        await self.send_view(embed, cog)

    async def send_group_help(self, group: Group):
        embed = await self.get_group_help(group)
        await self.send_view(embed, group)

    async def send_command_help(self, command: Command):
        embed = await self.get_command_help(command)
        await self.send_view(embed, command)


    async def get_bot_help(self, mapping: BotMapping) -> Embed:
        cogs = sorted(cog.qualified_name for cog in mapping if cog)

        embed = self.embed
        embed.title = 'Categories'
        embed.description = '\n'.join(['Categories:',
                                       '\n'.join(cogs), '',
                                       f'\n{self.no_category}:',
                                       *self.enumerate_commands(mapping[None])])
        return embed

    async def get_cog_help(self, cog: Cog) -> Embed:
        mapping = await self.get_filtered_mapping()
        commands = mapping[cog]

        embed = self.embed
        embed.title = f'{cog.qualified_name} Commands',
        embed.description = '\n'.join(self.enumerate_commands(commands))
        return embed

    async def get_group_help(self, group: Group) -> Embed:
        commands = await self.filter_commands(group.commands)

        embed = self.embed
        embed.title = group.qualified_name
        embed.description = '\n'.join([f'Usage: `{self.get_command_signature(group)}`', '',
                                       group.help, '',
                                       *self.enumerate_commands(commands)])
        return embed

    async def get_command_help(self, command: Command) -> Embed:
        embed = self.embed
        embed.title = command.qualified_name
        embed.description = '\n'.join([f'Usage: `{self.get_command_signature(command)}`',
                                       command.help])
        return embed


class HelpView(ui.View):
    def __init__(self, help: ComponentHelp,
                 mapping: BotMapping,
                 entity: Entity = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.help = help
        self.bot = help.context.bot

        self.mapping = mapping
        self.entity = entity

        self.update_cogs()

    async def on_timeout(self):
        await self.message.delete()

    def update_cogs(self):
        # to use emojis, you can build a list of `SelectOptions` then sort by label
        names = sorted(cog.qualified_name for cog in self.mapping if cog)
        # always add "No Category" at the end
        names.append(self.help.no_category)
        options = [SelectOption(label=name) for name in names]
        self.children[0].options = options

    async def update_commands(self):
        entity = self.entity

        # list the parent command/cog/bot's commands instead of nothing
        if isinstance(entity, Command) and not isinstance(entity, Group):
            entity = entity.parent or entity.cog or None

        if isinstance(entity, Group):
            cmds = await self.help.filter_commands(entity.commands)
        else:
            cmds = self.mapping[entity]

        options = [SelectOption(label=f'{cmd}') for cmd in cmds]
        self.children[1].options = options

    def get_embed(self) -> Coroutine[None, None, Embed]:
        entity = self.entity
        if isinstance(entity, Cog):
            return self.help.get_cog_help(entity)
        elif isinstance(entity, Group):
            return self.help.get_group_help(entity)
        elif isinstance(entity, Command):
            return self.help.get_command_help(entity)
        else:
            return self.help.get_bot_help(self.mapping)

    async def respond_with_edit(self, interaction: Interaction):
        embed = await self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.select(placeholder='Categories')
    async def cog_select(self, select: ui.Select, interaction: Interaction):
        name = select.values[0]
        entity = self.bot.get_cog(name)
        if entity == self.entity:
            return
        self.entity = entity

        await self.update_commands()
        await self.respond_with_edit(interaction)

    @ui.select(placeholder='Commands')
    async def command_select(self, select: ui.Select, interaction: Interaction):
        name = select.values[0]
        entity = self.bot.get_command(name)
        if entity == self.entity:
            return
        self.entity = entity

        await self.update_commands()
        await self.respond_with_edit(interaction)

    @ui.button(label='Up', style=ButtonStyle.blurple)
    async def up_level(self, button: ui.Button, interaction: Interaction):
        if isinstance(self.entity, Command):
            self.entity = self.entity.parent or self.entity.cog or None
        elif isinstance(self.entity, Cog):
            self.entity = None
        else:
            return
        await self.update_commands()
        await self.respond_with_edit(interaction)

    @ui.button(label='Close', style=ButtonStyle.danger)
    async def close(self, button: ui.Button, interaction: Interaction):
        self.stop()
        await interaction.message.delete()


class Help(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.original_help_command = bot.help_command
        bot.help_command = ComponentHelp(command_attrs=dict(hidden=True))
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.original_help_command


def setup(bot):
    bot.add_cog(Help(bot))