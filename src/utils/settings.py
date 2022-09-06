import json

from discord import Message


def get_prefix(_, message: Message) -> str:
    """
    Get Prefix

    Obtains the prefix for the server of the message.


    Args:
        message (var): The message who's server's prefix is needed

    Returns:
        str: The server's prefix.
    """
    with open("settings.json", "r") as f:
        prefixes = json.load(f)["prefixes"]

    if message.guild:
        return prefixes[str(message.guild.id)]
    else:
        return "s!"
