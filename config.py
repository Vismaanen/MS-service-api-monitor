"""
Configuration file for MS service api monitor script.
"""

# File / directory configuration
# Ensure script is being run with proper privileges in order to be able to create directories / files as configured.
DIR_MAIN = "C:\\Temp\\MS_service_API_monitor"
DIR_LOGS = f'{DIR_MAIN}\\Logs'
DIR_DB = f'{DIR_MAIN}\\Database'
DIR_IMAGES = f'{DIR_MAIN}\\Images'

# API endpoint settings
# both service health and announcements endpoints are a part of MS Graph
API_ENDPOINT_HEALTH = 'https://graph.microsoft.com/v1.0/admin/serviceAnnouncement/healthOverviews'
API_ENDPOINT_ANNOUNCE = 'https://graph.microsoft.com/v1.0/admin/serviceAnnouncement/messages'
API_ENDPOINT_AUTH = 'https://login.microsoftonline.com'
API_ENDPOINT_SCOPE = ["https://graph.microsoft.com/.default"]

# Service health state statuses map
# used in health percentage assessment and with charts creation
# update according to importance and order of each status
# https://learn.microsoft.com/en-us/graph/api/resources/servicehealth?view=graph-rest-1.0
STATUS_MAP = {
    "serviceOperational": 10,
    "serviceRestored": 9,  # consider as OK
    "falsePositive": 9,  # consider as OK
    "postIncidentReviewPublished": 9,  # consider as OK
    "resolved": 9,  # consider as OK
    "resolvedExternal": 9,  # consider as OK
    "serviceDegradation": 9,  # lower performance than operational, still working well, consider as OK
    "investigating": 8,
    "confirmed": 8,
    "reported": 8,
    "mitigatedExternal": 7,
    "mitigated": 7,
    "verifyingService": 6,
    "restoringService": 5,
    "extendedRecovery": 5,
    "serviceInterruption": 4,
    "investigationSuspended": 3,  # awaiting customer response / details
    "": 0
}

# Customer configuration section
# IMPORTANT: sensitive information stored in env variables in ";" delimited string format:
# tenantId;clientId;secretValue
# this dictionary stores names of customers and corresponding names of env variables
# for each customer set which services are to be monitored
CUSTOMERS = {
    'customer1': {
        'variable': 'API_CHECK_CUSTOMER1',
        'services': ['Intune', 'Microsoft365Defender'],
        'mail_to': 'recipient@domain.com',
        'mail_cc': ''
    },
    'customer2': {
        'variable': 'API_CHECK_CUSTOMER2',
        'services': ['Intune', 'Microsoft365Defender'],
        'mail_to': 'recipient@domain.com',
        'mail_cc': ''
    }
}

# Database scope limit
# determine after how many months data should be deleted
DB_DAYS_SCOPE = 30
DB_DAYS_PREV_FROM = 11
DB_DAYS_PREV_TO = 1

# Mailing configuration
# set SMTP server address, port and message details below
SMTP_SERVER = '192.168.1.1'
SMTP_PORT = 25
MAIL_FROM = 'sender@domain.com'
MAIL_SUBJECT = 'MS Service health report'
# for a custom signature: paste HTML code here
MAIL_SIGNATURE = '<hr><p style="color: gray;">This is an automated message - please do not reply.</p>'
