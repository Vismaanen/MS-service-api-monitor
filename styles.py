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
    return f'<tr><td style="width: 800px; text-align: center;"><img src="{path}"></tr>'


# append styled section title table row
def append_section_title(title: str) -> str:
    """
    Return report section title header.

    :param str title: section title
    :return: formatted section row
    :rtype: str
    """
    style_font = 'font-size: 18; color:#003780; '
    style_cell = f"text-align: left; height: 24px; "
    return f'<tr><td style="{style_cell}{style_font}"><strong>{title}</strong></td></tr>'


def append_service_state_record(service: str) -> str:
    """
    Return report section title header.

    :param str service: service state and percentage of occurrence
    :return: formatted section row
    :rtype: str
    """
    style_font = 'font-size: 14; color:#003780; '
    style_cell = f"text-align: left; height: 24px; "
    style_border = f"border-bottom: 1px solid silver; "
    return f'<tr><td style="{style_cell}{style_font}{style_border}">{service}</td></tr>'


def append_section_health(health: float) -> str:
    """
    Return report section title header.

    :param float health: section title
    :return: formatted section row
    :rtype: str
    """
    # validate health value / format
    try:
        value = int(health)
        notification = None
    except (ValueError, TypeError):
        value = 0
        notification = "wrong % value from service"

    # Define styles based on health ranges
    if 100 >= value >= 97:
        background = "#e3fad2"
        font_color = "#0f2400"
        border_color = "#071200"
    elif 97 > value >= 95:
        background = "#fff8d9"
        font_color = "#2b0000"
        border_color = "#300400"
    else:
        background = "#ffd9d9"
        font_color = "#2b0000"
        border_color = "#300400"

    # build unified style setting
    style = (
        f"text-align: left; "
        f"height: 24px; "
        f"font-size: 14; "
        f"color: {font_color}; "
        f"background-color: {background}; "
        f"border: 1px solid; "
        f"border-color: {border_color}; "
    )

    # append text content, return formatted table row
    content = f"Overall service health: {health}%"
    if notification:
        content += f" [{notification}]"
    return f"<tr><td style=\"{style}\">{content}</td></tr>"


def append_report_info() -> str:
    """
    Format and return report info header table row.

    :return: tr info content
    :rtype: str
    """
    style_font = 'font-size: 14; '
    style_cell = f"text-align: left; height: 24px; background-color: #e0e0e0;"
    style_border = f"border: 1px solid gray; "
    return (f'<tr><td style="{style_cell}{style_font}{style_border}">This report shows overall service health '
            f'percentage based on status data obtained from Microsoft Graph API. Data shown here may be used to '
            f'troubleshoot potential performance or accessibility issues with monitored Microsoft services. More '
            f'details on specific service states can be found within vendor resources listed below:'
            f'<ul>'
            f'<li><a href="https://learn.microsoft.com/en-us/graph/api/serviceannouncement-list-healthoverviews?view'
            f'=graph-rest-1.0" target="_blank">Resource list: [healthOverviews]</a></li>'
            f'<li><a href="https://learn.microsoft.com/en-us/graph/api/resources/servicehealth?view=graph-rest-1.0" '
            f'target="_blank">Description: [serviceHealth]</a></li>'
            f'<li><a href="https://learn.microsoft.com/en-us/graph/service-communications-concept-overview" '
            f'target="_blank">Description of [Service Communications]</a></li>'
            f'</ul></td></tr>')
