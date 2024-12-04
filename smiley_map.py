# The dictionnary
unicode_to_custom_smiley = {
    "😇": "<:angel:1313841199450427402>",
}

def get_custom_smiley(unicode_emoji):
    """Returns the custom smiley matching the emoji"""
    if unicode_emoji not in unicode_to_custom_smiley:
        raise ValueError(f"Custom smiley for {unicode_emoji} not found")
    return unicode_to_custom_smiley.get(unicode_emoji, None)