from discord.ext import commands


def need_db(command):
    """Decorator, not check, to mark the command as needing a DB connection."""
    command._db = True
    return command


def bot_config_attr(attr):
    return commands.check(lambda ctx: attr in ctx.bot.config)


def is_owner_check(ctx):
    return ctx.author.id == ctx.bot.owner.id


def is_owner():
    return commands.check(is_owner_check)


def check_permissions(ctx, perms):
    if is_owner_check(ctx):
        return True
    resolved = ctx.channel.permissions_for(ctx.author)
    return all(getattr(resolved, name, None) == value
               for name, value in perms.items())


def owner_or_permissions(**perms):
    return commands.check(lambda ctx: check_permissions(ctx, perms))
