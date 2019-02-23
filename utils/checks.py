from discord.ext import commands

import config


def config_attr(attr):
    return commands.check(lambda _: getattr(config, attr, None) is not None)


async def check_permissions(ctx, perms):
    if ctx.bot.app.owner.id == ctx.author.id:
        return True
    resolved = ctx.channel.permissions_for(ctx.author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())


def owner_or_permissions(**perms):
    return commands.check(lambda ctx: check_permissions(ctx, perms))


def dm_only():
    return commands.check(lambda ctx: ctx.guild is None)
