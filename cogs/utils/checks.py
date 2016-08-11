from discord.ext import commands


def is_owner_check(ctx):
    return ctx.message.author.id == ctx.bot.owner.id


def is_owner():
    return commands.check(is_owner_check)


def check_permissions(ctx, perms):
    if is_owner_check(ctx):
        return True
    resolved = ctx.message.channel.permissions_for(ctx.message.author)
    return all(getattr(resolved, name, None) == value
               for name, value in perms.items())


def owner_or_permissions(**perms):
    return commands.check(lambda ctx: check_permissions(ctx, perms))
