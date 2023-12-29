from PyQt6.QtGui import QColor, QPalette

theme_list = [
    "Dark",
    "Light",
    "System Default",
    "Wong (Colorblind Friendly)"
]

grp_dict = {
    "ACTIVE": QPalette.ColorGroup.Active,
    "INACTIVE": QPalette.ColorGroup.Inactive,
    "DISABLED": QPalette.ColorGroup.Disabled
}

role_dict = {
    "WINDOW_TEXT": QPalette.ColorRole.WindowText,
    "BUTTON": QPalette.ColorRole.Button,
    "LIGHT": QPalette.ColorRole.Light,
    "MID_LIGHT": QPalette.ColorRole.Midlight,
    "DARK": QPalette.ColorRole.Dark,
    "MID": QPalette.ColorRole.Mid,
    "TEXT": QPalette.ColorRole.Text,
    "BRIGHT_TEXT": QPalette.ColorRole.BrightText,
    "BUTTON_TEXT": QPalette.ColorRole.ButtonText,
    "BASE": QPalette.ColorRole.Base,
    "WINDOW": QPalette.ColorRole.Window,
    "SHADOW": QPalette.ColorRole.Shadow,
    "HIGHLIGHT": QPalette.ColorRole.Highlight,
    "HIGHLIGHTED_TEXT": QPalette.ColorRole.HighlightedText,
    "LINK": QPalette.ColorRole.Link,
    "LINK_VISITED": QPalette.ColorRole.LinkVisited,
    "ALTERNATE_BASE": QPalette.ColorRole.AlternateBase,
    "TOOLTIP_BASE": QPalette.ColorRole.ToolTipBase,
    "TOOLTIP_TEXT": QPalette.ColorRole.ToolTipText,
    "PLACEHOLDER_TEXT": QPalette.ColorRole.PlaceholderText
}


def change_theme(new_theme):
    """Update app theme based on user choice in settings window

    Args:
        new_theme (str): Predefined theme chosen from theme_list

    Returns:
        QPalette: Complete color palette swap for the app
    """
    match new_theme:
        case "Dark":
            dup_dict = {
                "WINDOW_TEXT": "#FFFFFF",
                "BUTTON": "#241F31",
                "LIGHT": "#80FFFFFF",
                "MID_LIGHT": "#2D263D",
                "DARK": "#80000000",
                "MID": "#000000",
                "TEXT": "#FFFFFF",
                "BRIGHT_TEXT": "#FFFFFF",
                "BUTTON_TEXT": "#FFFFFF",
                "BASE": "#000000",
                "WINDOW": "#241F31",
                "SHADOW": "#000000",
                "HIGHLIGHT": "#308CC6",
                "HIGHLIGHTED_TEXT": "#FFFFFF",
                "LINK": "#0000FF",
                "LINK_VISITED": "#FF00FF",
                "ALTERNATE_BASE": "#120F18",
                "TOOLTIP_BASE": "#FFFFDC",
                "TOOLTIP_TEXT": "#000000",
                "PLACEHOLDER_TEXT": "#80FFFFFF"
            }

            dark_dict = {
                "ACTIVE": dup_dict,
                "INACTIVE": dup_dict,
                "DISABLED": {
                    "WINDOW_TEXT": "#80FFFFFF",
                    "BUTTON": "#241F31",
                    "LIGHT": "#362E49",
                    "MID_LIGHT": "#2D263D",
                    "DARK": "#120F18",
                    "MID": "#181521",
                    "TEXT": "#120F18",
                    "BRIGHT_TEXT": "#FFFFFF",
                    "BUTTON_TEXT": "#80FFFFFF",
                    "BASE": "#241F31",
                    "WINDOW": "#241F31",
                    "SHADOW": "#000000",
                    "HIGHLIGHT": "#919191",
                    "HIGHLIGHTED_TEXT": "#FFFFFF",
                    "LINK": "#0000FF",
                    "LINK_VISITED": "#FF00FF",
                    "ALTERNATE_BASE": "#241F31",
                    "TOOLTIP_BASE": "#FFFFDC",
                    "TOOLTIP_TEXT": "#000000",
                    "PLACEHOLDER_TEXT": "#80FFFFFF"
                },
            }
            dark_palette = update_theme(dark_dict)
            return dark_palette
        case "Light":
            dup_dict = {
                "WINDOW_TEXT": "#000000",
                "BUTTON": "#EFEFEF",
                "LIGHT": "#FFFFFF",
                "MID_LIGHT": "#CACACA",
                "DARK": "#5E5C64",
                "MID": "#B8B8B8",
                "TEXT": "#000000",
                "BRIGHT_TEXT": "#FFFFFF",
                "BUTTON_TEXT": "#000000",
                "BASE": "#FFFFFF",
                "WINDOW": "#EFEFEF",
                "SHADOW": "#767676",
                "HIGHLIGHT": "#308CC6",
                "HIGHLIGHTED_TEXT": "#FFFFFF",
                "LINK": "#0000FF",
                "LINK_VISITED": "#FF00FF",
                "ALTERNATE_BASE": "#F7F7F7",
                "TOOLTIP_BASE": "#FFFFDC",
                "TOOLTIP_TEXT": "#000000",
                "PLACEHOLDER_TEXT": "#80000000"
            }

            light_dict = {
                "ACTIVE": dup_dict,
                "INACTIVE": dup_dict,
                "DISABLED": {
                    "WINDOW_TEXT": "#BEBEBE",
                    "BUTTON": "#EFEFEF",
                    "LIGHT": "#FFFFFF",
                    "MID_LIGHT": "#CACACA",
                    "DARK": "#BEBEBE",
                    "MID": "#B8B8B8",
                    "TEXT": "#BEBEBE",
                    "BRIGHT_TEXT": "#FFFFFF",
                    "BUTTON_TEXT": "#BEBEBE",
                    "BASE": "#EFEFEF",
                    "WINDOW": "#EFEFEF",
                    "SHADOW": "#B1B1B1",
                    "HIGHLIGHT": "#919191",
                    "HIGHLIGHTED_TEXT": "#FFFFFF",
                    "LINK": "#0000FF",
                    "LINK_VISITED": "#FF00FF",
                    "ALTERNATE_BASE": "#F7F7F7",
                    "TOOLTIP_BASE": "#FFFFDC",
                    "TOOLTIP_TEXT": "#000000",
                    "PLACEHOLDER_TEXT": "#80000000"
                },
            }
            light_palette = update_theme(light_dict)
            return light_palette
        case "System Default":
            sys_default = QPalette()
            return sys_default
        case "Wong (Colorblind Friendly)":
            dup_dict = {
                "WINDOW_TEXT": "#000000",
                "BUTTON": "#E69F00",
                "LIGHT": "#FFFFFF",
                "MID_LIGHT": "#000000",
                "DARK": "#000000",
                "MID": "#000000",
                "TEXT": "#000000",
                "BRIGHT_TEXT": "#FFFFFF",
                "BUTTON_TEXT": "#000000",
                "BASE": "#E69F00",
                "WINDOW": "#009E73",
                "SHADOW": "#009E73",
                "HIGHLIGHT": "#0072B2",
                "HIGHLIGHTED_TEXT": "#FFFFFF",
                "LINK": "#56B4E9",
                "LINK_VISITED": "#CC79A7",
                "ALTERNATE_BASE": "#E69F00",
                "TOOLTIP_BASE": "#FFFFDC",
                "TOOLTIP_TEXT": "#000000",
                "PLACEHOLDER_TEXT": "#80000000"
            }

            wong_dict = {
                "ACTIVE": dup_dict,
                "INACTIVE": dup_dict,
                "DISABLED": {
                    "WINDOW_TEXT": "#80000000",
                    "BUTTON": "#E69F00",
                    "LIGHT": "#FFFFFF",
                    "MID_LIGHT": "#FFFFFF",
                    "DARK": "#FFFFFF",
                    "MID": "#FFFFFF",
                    "TEXT": "#FFFFFF",
                    "BRIGHT_TEXT": "#000000",
                    "BUTTON_TEXT": "#80000000",
                    "BASE": "#E69F00",
                    "WINDOW": "#000000",
                    "SHADOW": "#F0E442",
                    "HIGHLIGHT": "#919191",
                    "HIGHLIGHTED_TEXT": "#000000",
                    "LINK": "#56b4E9",
                    "LINK_VISITED": "#CC79A7",
                    "ALTERNATE_BASE": "#919191",
                    "TOOLTIP_BASE": "#000000",
                    "TOOLTIP_TEXT": "#FFFFFF",
                    "PLACEHOLDER_TEXT": "#80000000"
                },
            }
            wong_palette = update_theme(wong_dict)
            return wong_palette
        case _:
            print("There was an error parsing themes.")


def update_theme(cur_dict):
    """Recursive function to parameterize theme dictionary and return palette

    Args:
        cur_dict (dict): Self-explanatory

    Return:
        QPalette: Self-explanatory
    """
    new_palette = QPalette()

    for group in cur_dict:
        cur_grp = grp_dict[group]

        for color in cur_dict[group]:
            cur_role = role_dict[color]
            new_palette.setColor(cur_grp, cur_role, QColor(cur_dict[group][color]))

    return new_palette
