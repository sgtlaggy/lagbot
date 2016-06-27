from discord.ext import commands

from .load_config import load_config

owner_id = load_config()['owner_id']

def is_owner_check(message):
    return message.author.id == owner_id


def is_owner():
    return commands.check(lambda ctx: is_owner_check(ctx.message))


def check_permissions(ctx, perms):
    msg = ctx.message
    if is_owner_check(msg):
        return True
    resolved = msg.channel.permissions_for(msg.author)
    return all(getattr(resolved, name, None) == value
               for name, value in perms.items())

def owner_or_permissions(**perms):
    def predicate(ctx):
        return check_permissions(ctx, perms)
    return commands.check(predicate)
