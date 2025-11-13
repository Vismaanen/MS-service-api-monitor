"""
HTML styles and utilities for MS service api monitor reports.
"""


# default font style for a report
# customize freely
def font_style() -> str:
    """
    Return font style marking for use with ``<style>`` definitions.

    :return: font style string
    :rtype: str
    """
    return "font-family: \'Courier New\', monospace; font-size: 14;"


# table header record

def set_theader() -> str:
    """
    Return code of a new table with default settings related to cell spacing and padding.

    :param int width: table width in px
    :return: ``html`` table header
    :rtype: str
    """
    html_string = (
        f'<table style="width: 800px; '
        f'border-collapse: collapse; '
        f'border-spacing: 0cm; '
        f'{font_style()} '
        f'cellpadding="5">'
        f'<tbody>'
    )
    return html_string


# table closure record
def close_theader() -> str:
    """
    Return table closing string.

    :return: ``</tbody></table>``
    :rtype: str
    """
    return "</tbody></table>"


# add table row containing image
def add_image_tr(path: str) -> str:
    """
    Return table row containing image path.

    :param str path: image path
    :return: formatted image tr code
    :rtype: str
    """
    return f'<tr><td style="width: 800px; text-align: center;"><img src="cid:{path}"></tr>'


# append styled section title table row
def append_section_title(title: str) -> str:
    """
    Return report section title header.

    :param str title: section title
    :return: formatted section row
    :rtype: str
    """
    style_border = 'border-bottom: 2px solid black; '
    style_font = 'font-size: 18; color:#003780; '
    style_cell = f"text-align: left; height: 24px; "
    return f'<tr><td style="{style_cell}{style_border}{style_font}"><strong>{title}</strong></td></tr>'


def append_section_health(health: float) -> str:
    """
    Return report section title header.

    :param float health: section title
    :return: formatted section row
    :rtype: str
    """
    # check value if correct
    try:
        value = int(health)
        notification = None
    except ValueError:
        value = 0
        notification = 'wrong % value from service'
    # set color format depending on a health
    if 100 >= value >= 97:
        style_font = 'font-size: 18; color:#041200; '
        style_cell = f"text-align: left; height: 24px; background-color: #fcc5c5; "
    if 97 > value >= 95:
        style_font = 'font-size: 18; color:#2b0000; '
        style_cell = f"text-align: left; height: 24px; background-color: #fff8d9; "
    else:
        style_font = 'font-size: 18; color:#2b0000; '
        style_cell = f"text-align: left; height: 24px; background-color: #ffd9d9; "
    # return formatted cell
    style_border = 'border-bottom: 2px solid black; '
    if notification:
        return f'<tr><td style="{style_cell}{style_border}{style_font}"><strong>{health}%</strong> [{notification}]</td></tr>'
    return f'<tr><td style="{style_cell}{style_border}{style_font}"><strong>{health}%</strong></td></tr>'

