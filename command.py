"""Module containing Command class."""


class Command():
    """Command class."""

    def __init__(self, name, func, servers, users):
        """Command constructor."""
        self.name = name
        self.func = func
        self.servers = servers
        self.users = users

    def __str__(self):
        """String representation of Command."""
        return self.name
