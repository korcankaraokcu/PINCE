from PyQt6.QtGui import QColor, QPalette


# TODO: Previewing themes in settings window would drastically increase usability
def change_theme(new_theme):
    """Update app theme based on user choice in settings window

    Args:
        new_theme (str): Predefined theme chosen from theme_list

    Returns:
        QPalette: Complete color palette swap for the app
    """
    match new_theme:
        case "Dark":
            dup_dict = {"WINDOW_TEXT": "#FFFFFF",
                        "BUTTON": "#241F31",
                        "LIGHT": "#362E49",
                        "MID_LIGHT": "#2D263D",
                        "DARK": "#120F18",
                        "MID": "#181521",
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
                        "PLACEHOLDER_TEXT": "#80FFFFFF"}

            dark_dict = {
                "ACTIVE": dup_dict,
                "INACTIVE": dup_dict,
                "DISABLED": {"WINDOW_TEXT": "#120F18",
                             "BUTTON": "#241F31",
                             "LIGHT": "#362E49",
                             "MID_LIGHT": "#2D263D",
                             "DARK": "#120F18",
                             "MID": "#181521",
                             "TEXT": "#120F18",
                             "BRIGHT_TEXT": "#FFFFFF",
                             "BUTTON_TEXT": "#120F18",
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
                             "PLACEHOLDER_TEXT": "#80FFFFFF"},
            }
            dark_palette = update_theme(dark_dict)
            return dark_palette
        case "Light":
            dup_dict = {"WINDOW_TEXT": "#000000",
                        "BUTTON": "#EFEFEF",
                        "LIGHT": "#FFFFFF",
                        "MID_LIGHT": "#CACACA",
                        "DARK": "#9F9F9F",
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
                "DISABLED": {"WINDOW_TEXT": "#BEBEBE",
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
                             "PLACEHOLDER_TEXT": "#80000000"},
            }
            light_palette = update_theme(light_dict)
            return light_palette
        case "System Default":
            sys_default = QPalette()
            return sys_default
        case "Wong (Colorblind Friendly)":
            dup_dict = {"WINDOW_TEXT": "#000000",
                        "BUTTON": "#E69F00",
                        "LIGHT": "#000000",
                        "MID_LIGHT": "#000000",
                        "DARK": "#000000",
                        "MID": "#000000",
                        "TEXT": "#000000",
                        "BRIGHT_TEXT": "#FFFFFF",
                        "BUTTON_TEXT": "#000000",
                        "BASE": "#E69F00",
                        "WINDOW": "#F0E442",
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
                "DISABLED": {"WINDOW_TEXT": "#D55E00",
                             "BUTTON": "#D55E00",
                             "LIGHT": "#FFFFFF",
                             "MID_LIGHT": "#FFFFFF",
                             "DARK": "#FFFFFF",
                             "MID": "#FFFFFF",
                             "TEXT": "#FFFFFF",
                             "BRIGHT_TEXT": "#000000",
                             "BUTTON_TEXT": "#D55E00",
                             "BASE": "#D55E00",
                             "WINDOW": "#000000",
                             "SHADOW": "#F0E442",
                             "HIGHLIGHT": "#919191",
                             "HIGHLIGHTED_TEXT": "#000000",
                             "LINK": "#56b4E9",
                             "LINK_VISITED": "#CC79A7",
                             "ALTERNATE_BASE": "#919191",
                             "TOOLTIP_BASE": "#000000",
                             "TOOLTIP_TEXT": "#FFFFFF",
                             "PLACEHOLDER_TEXT": "#80000000"},
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
    cur_grp = None
    cur_role = None

    for group in cur_dict:
        match group:
            case "ACTIVE":
                cur_grp = QPalette.ColorGroup.Active
            case "INACTIVE":
                cur_grp = QPalette.ColorGroup.Inactive
            case "DISABLED":
                cur_grp = QPalette.ColorGroup.Disabled
            case _:
                print("There was an error parsing theme groups.")

        for color in cur_dict[group]:
            match color:
                case "WINDOW_TEXT":
                    cur_role = QPalette.ColorRole.WindowText
                case "BUTTON":
                    cur_role = QPalette.ColorRole.Button
                case "LIGHT":
                    cur_role = QPalette.ColorRole.Light
                case "MID_LIGHT":
                    cur_role = QPalette.ColorRole.Midlight
                case "DARK":
                    cur_role = QPalette.ColorRole.Dark
                case "MID":
                    cur_role = QPalette.ColorRole.Mid
                case "TEXT":
                    cur_role = QPalette.ColorRole.Text
                case "BRIGHT_TEXT":
                    cur_role = QPalette.ColorRole.BrightText
                case "BUTTON_TEXT":
                    cur_role = QPalette.ColorRole.ButtonText
                case "BASE":
                    cur_role = QPalette.ColorRole.Base
                case "WINDOW":
                    cur_role = QPalette.ColorRole.Window
                case "SHADOW":
                    cur_role = QPalette.ColorRole.Shadow
                case "HIGHLIGHT":
                    cur_role = QPalette.ColorRole.Highlight
                case "HIGHLIGHTED_TEXT":
                    cur_role = QPalette.ColorRole.HighlightedText
                case "LINK":
                    cur_role = QPalette.ColorRole.Link
                case "LINK_VISITED":
                    cur_role = QPalette.ColorRole.LinkVisited
                case "ALTERNATE_BASE":
                    cur_role = QPalette.ColorRole.AlternateBase
                case "TOOLTIP_BASE":
                    cur_role = QPalette.ColorRole.ToolTipBase
                case "TOOLTIP_TEXT":
                    cur_role = QPalette.ColorRole.ToolTipText
                case "PLACEHOLDER_TEXT":
                    cur_role = QPalette.ColorRole.PlaceholderText
                case _:
                    print("There was an error parsing theme colors.")

            new_palette.setColor(cur_grp, cur_role, QColor(cur_dict[group][color]))

    return new_palette
