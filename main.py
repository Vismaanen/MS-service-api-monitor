"""
Subject         : Microsoft API service health check script.
Description     : Script performs two separate functions:

                - enables continuous logging of selected Microsoft service states into a local SQLite database,
                - enables creation of a report of service health states logged previously:
                - for all customers,
                - for a selected customer.

Dependencies    : pip install msal sqlite3 requests matplotlib
"""

# default libs
import os
import smtplib
import sys
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import msal
import sqlite3
import logging
import requests
import argparse
import config as c
import styles as s
import pandas as pd
import matplotlib.pyplot as plt

# additional utilities
from typing import Any
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter


def main(**kwargs) -> None:
    """
    Main executable to carry out service health check, logging results into local file or preparing and sending a
    summary report.

    :param kwargs: script run arguments\
    :type kwargs: dict[str, Any]
    """
    # create log file
    log = create_log()
    if not log:
        exit()

    # check provided script mode
    # if mode not provided - ask for user input
    if not kwargs['mode']:
        mode = select_mode(log)
    else:
        mode = kwargs['mode']

    # check customer
    if not kwargs['customer']:
        customer = 'None'
    else:
        customer = kwargs['customer']

    # run selected task
    if mode == 'scan':
        perform_api_health_scan(log)

    if mode == 'report':
        create_health_report(log, customer)


# UTILITY FUNCTIONS --------------------------------------------------
def create_log() -> logging.Logger or exit:
    """
    Create and return app log file object.

    :return: log object
    :rtype: logging.Logger
    """
    # log parameters
    log_name = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    try:
        # adjust target logs directory as needed - by default: subdirectory in a script location
        log_directory = Path(f"{c.DIR_LOGS}")
        log_directory.mkdir(parents=True, exist_ok=True)
        log_path = log_directory / log_name
        # create logger
        logger = logging.getLogger(log_name)
        logger.setLevel(logging.INFO)
        # file handler setting
        if not logger.handlers:
            file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(file_handler)
            # console output handler setting
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(console_handler)
        return logger
    except Exception as exc:
        print(f"Cannot create local log object: {str(exc)}; script will now exit.")
        exit()


def args_parser() -> dict[str, Any]:
    """
    Parse provided arguments.

    :return: dictionary of arguments
    :rtype: dict[str, Any]
    """
    parser = argparse.ArgumentParser(description='MS-service-api-monitor')
    parser.add_argument('-m', '--mode', metavar='mode', help='Provide task to perform', type=str)
    parser.add_argument('-c', '--customer', metavar='customer', help='Provide customer name', type=str)
    args = parser.parse_args()
    return vars(args)


def select_mode(log: logging.Logger) -> str or exit:
    """
    Enabled manual input of application mode, providing a list of possible options. Exit on improper mode value.

    :param log: log object
    :type log: logging.Logger
    :return: chosen mode string
    :rtype: str
    """
    log.info('select task to perform')
    log.info('scan - connect with customer API to obtain service health info')
    log.info('report - prepare a summary service health report email')
    # get user input
    mode = input(f"Chosen task [scan / report]: ")
    # verify input - if in range, return proper mode string
    if mode in ['scan', 'report']:
        log.info(f'proceeding with {mode}')
        return mode
    else:
        log.critical(f'Option [{mode}] not recognized, exiting...')
        exit()


def ask_for_customer(customer: str, log: logging.Logger) -> str or exit:
    """
    Ask for a user input to get customer name to proceed with a report.

    :param str customer: provided customer name or 'None' string
    :param log: log object
    :type log: logging.Logger
    :return: chosen customer name, validated against configuration
    :rtype: str
    """
    if customer == 'None':
        # ask for customer selection
        log.info('customer argument not provided - options:')
        log.info('> all')
        for customer in c.CUSTOMERS:
            log.info(f'> {customer}')
        customer = input(f"Chosen customer: ")
    # validate response
    if customer not in [name for name, config in c.CUSTOMERS.items()] and customer != 'all':
        log.warning('> customer not recognized in configuration, exiting...')
        exit()
    else:
        log.info('> customer valid, proceeding')
        return customer.lower()


def check_database() -> bool:
    """
    Check if local database already exists in its directory.

    :return: True or False
    :rtype: bool
    """
    db_path = os.path.join(c.DIR_DB, "ServiceDB.db")
    return os.path.exists(db_path)


def get_env_variable(name: str, log: logging.Logger) -> str | None:
    """
    Attempt to obtain environmental variable for a given customer.

    :param str name: environment variable name string
    :param log: log object
    :type log: logging.Logger
    :return: variable value string, optional
    :rtype: str or None
    :raise Exception: environmental variable search exception
    """
    try:
        env_value = os.getenv(name)
        if not env_value:
            log.warning(f'> cannot find local environment variable [{name}]')
            return None
        else:
            return env_value
    except Exception as exc:
        log.warning(f'> error while searching for local environment variable [{name}]: {exc}')
        return None


# API FUNCTIONS ------------------------------------------------------
def perform_api_health_scan(log: logging.Logger) -> None:
    """
    Main executable to obtain customers service health statuses.

    :param log: log object
    :type log: logging.Logger
    :raise Exception: general unspecified API check code exception
    """
    health = {}
    try:
        # check if local SQLite database is present, create one if not
        if not check_database():
            create_local_db(log)
        # get configured customers
        # per customer: obtain env variable API credentials, then request API services info
        log.info('checking configured customers')
        customers = c.CUSTOMERS
        if not customers:
            log.warning(f'> no customers configured in config file, exiting')
            exit()
        # for each customer check configured services health
        for customer in customers:
            log.info('-------------------')
            log.info(f'customer: {customer}')
            # obtain credentials
            # raw_credentials = get_env_variable(customers[customer]['variable'])
            _raw_credentials = customers[customer]['fallback']
            # get customer monitored services
            services = customers[customer]['services']
            # attempt to obtain auth token
            _token = ms_authenticate(_raw_credentials, log)
            if not _token:
                continue
            # attempt to call API service for health data
            if raw_data := ms_get_data(customer, _token, services, log):
                health[customer] = raw_data
        # upload results
        if health:
            # upload data
            upload_health_results(health, log)
            # wipe all data older than X months
            delete_outdated_records(log)
        else:
            log.warning('no health data to save')
    # handle any unexpected exception
    except Exception as exc:
        log.error(f'> general unexpected exception: {exc}')


def ms_authenticate(raw_credentials: str, log: logging.Logger) -> str | None:
    """
    Attempt to obtain authentication token for a customer.

    :param str raw_credentials: environment variable credentials string
    :param log: log object
    :type log: logging.Logger
    :return: obtained token string, optional
    :rtype: str or None
    :raise Exception: authentication unexpected exception
    """
    try:
        tenant_id, client_id, secret = raw_credentials.split(";")
        log.info(f'configuring MSAL client for authentication')
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=secret,
            authority=f'{c.API_ENDPOINT_AUTH}/{tenant_id}'
        )
        # perform request
        result = app.acquire_token_silent(c.API_ENDPOINT_SCOPE, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=c.API_ENDPOINT_SCOPE)
        # validate results
        if "access_token" in result:
            log.info('> token obtained')
            return result["access_token"]
        else:
            log.warning(f'> authentication failed: {result.get("error_description")}')
            return None
    except Exception as exc:
        log.error(f'> general auth code exception: {exc}')
        return None


def ms_get_data(customer: str, _token: str, services: list[Any], log: logging.Logger) -> list[Any] | None:
    """
    Attempt to obtain current service health data for a customer from Graph API.

    :param str customer: customer name
    :param str _token: API auth token string
    :param services: list of services enabled for health monitoring for a customer
    :param log: log object
    :type services: list[str]
    :type log: logging.Logger
    :return: obtained health data list
    :rtype: list[Any] or None
    :raise Exception: API request exception
    """
    results = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # set conenction headers
    headers = {
        "Authorization": f"Bearer {_token}",
        "Content-Type": "application/json"
    }
    # call API endpoint
    try:
        response = requests.get(c.API_ENDPOINT_HEALTH, headers=headers)
        if response.status_code == 200:
            data = response.json()['value']
            for item in data:
                if item['id'] in services:
                    log.info(f'> {item['service']}: {item['status']}')
                    results.append([customer, timestamp, item['service'], item['status']])
            return results
        else:
            log.warning(f'> request failed: {response.status_code}')
            log.warning(f'> {response.text}')
            return None
    except Exception as exc:
        log.error(f'> error while executing API request: {exc}')
        return None


# REPORT FUNCTIONS
def create_health_report(log: logging.Logger, customer: str) -> None:
    """
    Attempt to create and send a report containing daily health overview.

    :param log: log object
    :param str customer: customer name or 'all' string
    :type log: logging.Logger
    :raise Exception: general report build exception
    """
    # customer validation
    # check if a customer was provided as an argument
    # if not - proceed with asking for an input
    customer = ask_for_customer(customer, log)
    # collect data
    # structure into a dictionary
    # analyze data to create tables for charts, calculate percentages
    # finally create a *.html report, forward as email
    if data := get_daily_report_data(log, customer):
        # create report content
        if raw_content := format_report_content(data, log):
            # calculate percents, create images
            if analysis := analyze_service_health(raw_content, log):
                # forward report
                if reports := create_report_body(analysis, log):
                    send_report(reports, log)


def get_daily_report_data(log: logging.Logger, customer: str) -> list[Any] | None:
    """
    Attempt to obtain data from a previous day for a given customer or all customers.

    :param log: log object
    :param str customer: customer name or 'all' string
    :type log: logging:Logger
    :return: list of customer data, optional
    :rtype: list[Any] or None
    :raise Exception: data retrieval exception
    """
    results = []
    log.info(f'obtaining report data: {customer} customer(s)')
    try:
        # validate customer name
        # skip this part if 'all' customers chosen
        query, params = set_report_data_query(customer, log)
        # execute query
        results = get_report_data(query, params, log)
        # validate data volume
        if not results:
            log.warning(f'> no data for [{customer}] customer(s) obtained from database')
            return None
        log.info('> data obtained')
        return results
    # anticipate exceptions
    except Exception as exc:
        log.error(f'> cannot obtain daily report data: {exc}')
    finally:
        return results if results else None


def analyze_service_health(data: dict[str, Any], log: logging.Logger) -> dict[str, Any] | None:
    """
    Perform tasks related to calculation of performance and creation of charts per customer > service.

    :param data: structured customer > service health raw data
    :param log: log object
    :type data: dict[str, Any]
    :type log: logging.Logger
    :return: report data dictionary, optional
    :rtype: dict[str, Any] or None
    """
    results = {}
    log.info('-------------------')
    log.info('customer service health analysis for a report')
    # calculate per-service > per-state percentages
    for customer in data:
        log.info(f'customer: {customer}')
        customer_report = {}
        # loop services
        for service in data[customer]:
            log.info(f'service: {service}')
            customer_report[service] = {
                'chart': create_health_chart(customer, service, data[customer][service], log),
                'percentages': calculate_health_percent(data[customer][service], log)
            }
        # validate content
        if all(value is None for value in customer_report.values()):
            log.warning('> could not create chart and calculate health %, skipping')
            continue
        else:
            results[customer] = customer_report
    # final validation and return
    return results if results else None


def create_health_chart(customer: str, service: str, data: list[Any], log: logging.Logger) -> str | None:
    """
    Attempt to create service health chart showing status changes over time.

    :param str customer: customer name
    :param str service: service name
    :param data: service health data records list
    :param log: log object
    :type data: list[Any]
    :type log: logging.Logger
    :return: image path string, optional
    :rtype: str or None
    :raise Exception: image processing or saving exception
    """
    # check images directory
    image_directory = Path(f"{c.DIR_IMAGES}\\{customer}")
    image_directory.mkdir(parents=True, exist_ok=True)
    # proceed with image creation
    log.info(f'> creating chart')
    try:
        # create dataframe
        df = pd.DataFrame(data, columns=['timestamp', 'status'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['value'] = df['status'].map(c.STATUS_MAP)
        # set consolas font for report consistency
        plt.rcParams['font.family'] = 'Consolas'
        # create chart object
        plt.figure(figsize=(10, 4))
        plt.plot(df['timestamp'], df['value'], drawstyle='steps-post', linewidth=1, color='steelblue', marker='.')
        # format chart object
        plt.yticks(list(c.STATUS_MAP.values()), list(c.STATUS_MAP.keys()))
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        # for test purposes image can be shown
        # plt.show()
        # save image
        filename = f'{image_directory}\\{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_{service}.png'
        plt.savefig(filename)
        plt.close()
        log.info('> ok')
        return filename
    except Exception as exc:
        log.warning(f'> cannot create / save chart: {exc}')
        return None


def calculate_health_percent(data: list[Any], log: logging.Logger) -> list[Any] | None:
    """
    Attempt to calculate percentage of health for a service based on obtained status raw data.

    :param data: service health data records list
    :param log: log object
    :type data: list[Any]
    :type log: logging.Logger
    :return: list of health percentage results, optional
    :rtype: list[Any] or None
    """
    results = None
    log.info('> calculating service health %')
    try:
        statuses = [status for _, status in data]
        mapped = [c.STATUS_MAP.get(status, 0) for status in statuses]
        # based on a status map - summarize OK's
        ok_count = sum(1 for state in mapped if state >= 9)
        # get total items count
        total = len(mapped)
        # calculate overall OK / NOK percentage
        ok_percentage = (ok_count / total) * 100 if total > 0 else 0
        # count each status occurrence percentage
        counter = Counter(statuses)
        percentages = {key: (value / total) * 100 for key, value in counter.items()}
        results = {
            "overall": ok_percentage,
            "services": percentages
        }
        log.info('> ok')
    except Exception as exc:
        log.error(f'> cannot calculate health percentages: {exc}')
    finally:
        return results if results else None


# SQLITE FUNCTIONS ------------------------------------------------------
def create_local_db(log: logging.Logger):
    """
    Attempt to create local SQLite database for service health data storage. Exit script on failure.

    :param log: log object
    :type log: logging.Logger
    :raise Exception: database creation exception: check permissions to write in a configured db location
    """
    try:
        log.info(f'attempting to create local SQLite database')
        # create database directory if needed
        path = Path(f"{c.DIR_DB}")
        path.mkdir(parents=True, exist_ok=True)
        # check if database is there
        db_path = os.path.join(f"{c.DIR_DB}", "ServiceDB.db")
        # create database with health data table
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_status (
                    customer TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    service TEXT NOT NULL,
                    status TEXT NOT NULL)
            """)
            conn.commit()
        log.info(f'> ok')
    except Exception as exc:
        log.error(f'> error while creating local SQLite database at {c.DIR_DB}: {exc}')
        exit()


def upload_health_results(health: dict[str, Any], log: logging.Logger) -> None:
    """
    Perform upload of obtained service health data into local database.

    :param health: customer service health data
    :param log: log object
    :type health: dict[str, Any]
    :type log: logging.Logger
    :raise Exception: data upload exception
    """
    conn = None
    log.info('-------------------')
    log.info('saving health data to local database')
    try:
        # create connection
        conn = sqlite3.connect(os.path.join(f"{c.DIR_DB}", "ServiceDB.db"))
        cursor = conn.cursor()
        # loop customers
        for customer in health:
            data = health[customer]
            placeholders = ", ".join(["?"] * len(data[0]))
            query = f"INSERT INTO service_status VALUES ({placeholders})"
            cursor.executemany(query, data)
            conn.commit()
        # close cursor and connection
        cursor.close()
        log.info('> data uploaded')
    except Exception as exc:
        log.error(f'> cannot upload data: {exc}')
    finally:
        conn.close()


def delete_outdated_records(log: logging.Logger) -> None:
    """
    Attempt to delete records older than configured days limit.

    :param log: log object
    :type log: logging.Logger
    :raise Exception: data delete exception: validate query and database state
    """
    conn = None
    try:
        # create connection
        conn = sqlite3.connect(os.path.join(f"{c.DIR_DB}", "ServiceDB.db"))
        cursor = conn.cursor()
        # set limit timestamp
        cutoff_date = (datetime.now() - timedelta(days=c.DB_DAYS_SCOPE)).strftime("%Y-%m-%d")
        # execute query
        query = f"DELETE FROM service_status WHERE timestamp < ?"
        cursor.execute(query, (cutoff_date,))
        deleted = cursor.rowcount
        conn.commit()
        log.info(f"> {deleted} records older than {c.DB_DAYS_SCOPE} removed from db")
    except Exception as exc:
        log.error(f'> cannot delete outdated data: {exc}')
    finally:
        conn.close()


def get_report_data(query: str, params: tuple[Any], log: logging.Logger) -> list[Any] | None:
    """
    Attempt to obtain report data

    :param str query: database query string
    :param params: query parameters: timestamps and optionally customer name
    :param log: log object
    :type params: tuple[Any]
    :type log: logging.Logger
    :return: list of records, optional
    :rtype: list[Any] or None
    :raise Exception: data fetch exception
    """
    results = None
    conn = None
    log.info('executing report data query')
    try:
        # create connection
        conn = sqlite3.connect(os.path.join(f"{c.DIR_DB}", "ServiceDB.db"))
        cursor = conn.cursor()
        # execute query
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        log.info(f'> data query executed')
    # anticipate exceptions
    except Exception as exc:
        log.error(f'> cannot obtain data from database: {exc}')
    finally:
        conn.close()
        return results if results else None


def set_report_data_query(customer: str, log: logging.Logger) -> tuple[str, Any]:
    """
    Set query and parameters for report data fetch.

    :param str customer: customer name or 'all' string
    :param log: log object
    :type log: logging:Logger
    :return: tuple containing query and query parameters
    :rtype: tuple[str, Any]
    :raise Exception: timestamp calculation exception due to improper value setting
    """
    # timestamp parameters
    log.info('setting report data query and parameters')
    try:
        date_from = datetime.now() - timedelta(days=c.DB_DAYS_PREV_FROM)
        date_to = datetime.now() - timedelta(days=c.DB_DAYS_PREV_TO)
    except Exception as exc:
        log.warning(f'> provided incorrect [DB_DAYS_PREV_FROM] or [DB_DAYS_PREV_TO] value: {exc}')
        log.info(f'> defaulting to 1 day ago')
        date_from = datetime.now() - timedelta(days=1)
        date_to = datetime.now() - timedelta(days=1)
    # calculate from-to timestamps
    start_time = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = date_to.replace(hour=23, minute=59, second=59, microsecond=0)
    # create query
    if customer == 'all':
        query = "SELECT * FROM service_status WHERE timestamp BETWEEN ? AND ?"
        params = (start_time.strftime("%Y-%m-%d %H:%M:%S"), end_time.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        query = "SELECT * FROM service_status WHERE timestamp BETWEEN ? AND ? AND customer = ?"
        params = (start_time.strftime("%Y-%m-%d %H:%M:%S"), end_time.strftime("%Y-%m-%d %H:%M:%S"), customer)
    return query, params


# REPORT FUNCTIONS ----------------------------------------------------
def format_report_content(data: list[str], log: logging.Logger) -> dict[str, Any] | None:
    """
    Format obtained raw data records into a dictionary: per-customer > per-service.

    :param data: service health raw data list from database
    :param log: log object
    :type data: list[Any]
    :type log: logging.Logger
    :return: per-customer-service dictionary of service states and corresponding timestamps, optional
    :rtype: dict[str, Any] or None
    :raise Exception: data parsing exception due to possible data format corruption
    """
    results = {}
    try:
        # get unique customers
        customers = list(set([item[0] for item in data]))
        # obtain data per customer
        for customer in customers:
            # get customer-only records
            customer_data = [list(item) for item in data if item[0] == customer]
            # create per-service dictionary
            customer_services = list(set(item[2] for item in customer_data))
            customer_dict = {}
            for service in customer_services:
                customer_dict[service] = [[item[1], item[3]] for item in customer_data if item[2] == service]
            # append results to a summary customers dict
            results[customer] = customer_dict
    except Exception as exc:
        log.error(f'> issue with data formatting: {exc}')
    finally:
        return results if results else None


def create_report_body(analysis: dict[str, Any], log: logging.Logger) -> dict[str, Any] | None:
    """
    Attempt to create email report body per customer.

    :param analysis: report content object: per customer > service
    :param log: log object
    :type analysis: dict[str, Any]
    :type log: logging.Logger
    :return: dictionary of per-customer *.html mail body strings, optional
    :rtype: dict[str, str] or None
    :raise Exception: *.html code build exception
    """
    results = {}
    try:
        # default per-customer steps
        for customer in analysis:
            customer_data = analysis[customer]
            # create table header
            html_string = s.set_theader()
            # add services sections
            for service in analysis[customer]:
                service_data = analysis[customer][service]
                html_string += s.set_theader()
                # append service name row
                html_string += s.append_section_title(f'⚙️ {service}')
                # append overall service compliance record
                if service_data["percentages"]["overall"]:
                    html_string += s.append_section_health(service_data["percentages"]["overall"])
                # append chart object with link
                if service_data['chart']:
                    html_string += s.add_image_tr(service_data['chart'])
                # append per-service state occurrence %
                if service_data["percentages"]["services"]:
                    html_string += s.append_service_state_record(f'<strong>Service health states occurrence:</strong>')
                    for state, occurrence in service_data["percentages"]["services"].items():
                        html_string += s.append_service_state_record(f'{state}: {occurrence}%')
                # close service table header
                html_string += s.close_theader()
                html_string += '</br>'
            # close overall table header
            html_string += s.close_theader()
            # append to dict
            customer_data['html'] = html_string
            results[customer] = customer_data
    except Exception as exc:
        log.error(f'> cannot create report email body: {exc}')
    finally:
        return results if results else None


def send_report(reports: dict[str, Any], log: logging.Logger) -> None:
    """
    Attempt to send a report via SMTP.

    :param reports: report data dictionary - with analysis and image paths as well as *.html report code
    :param log: log object
    :type reports: dict[str, Any]
    :type log: logging.Logger
    :raise Exception: ``exc`` SMTP connection failure exception, skipping other steps
    :raise Exception: ``exd`` email object creation exception
    :raise Exception: ``exe`` email sending exception
    """
    # global variables setting
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    # separate reports per customer
    for customer in reports:
        # get html body
        html_body = reports[customer]['html']
        # combine list of file paths for email cid replacement and files attachment
        files = [value['chart'] for key, value in reports[customer].items() if key != 'html' and 'chart' in value]
        # test / connect with SMTP

        # connect with a server
        # failure will throw an exception exiting a script
        try:
            server = smtplib.SMTP(c.SMTP_SERVER, c.SMTP_PORT)
        except Exception as exc:
            log.error(f'> cannot connect with SMTP: {exc}')
            exit()

        # if connection successful - create a message
        try:
            message_object = MIMEMultipart()
            # attach signature
            # signature_image = MIMEImage(open('C:\\ECS\\Resources\\signature.png', 'rb').read())
            # signature_image.add_header('Content-ID', '<signature>')
            # message_object.attach(signature_image)
            # assign other properties
            message_object["From"] = c.MAIL_FROM
            message_object["To"] = c.CUSTOMERS[customer]['mail_to']
            message_object["Cc"] = c.CUSTOMERS[customer]['mail_cc']
            message_object["Subject"] = f'[{customer}] {c.MAIL_SUBJECT} - {timestamp}'
            # append charts as attachments
            # for each file create simple cid
            # then replace paths in html code with cids
            for path in files:
                with open(path, "rb") as f:
                    img = MIMEImage(f.read())
                    # create cid
                    cid = os.path.basename(path).replace(" ", "_")
                    # append file to message
                    img.add_header("Content-ID", f"<{cid}>")
                    img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
                    message_object.attach(img)
                    # replace original path with a cid to enable displaying image in email body
                    html_body = html_body.replace(path, f"cid:{cid}")
            # attach parsed email body
            message_body = f'Hello, <br /><br />{html_body}{c.MAIL_SIGNATURE}'
            message_object.attach(MIMEText(message_body, "html", "utf-8"))
        except Exception as exd:
            log.error(f'> message creation exception: {exd}')
            continue

        # send message, notify if failed
        try:
            server.send_message(message_object)
            log.info(f'> email sent')
        except Exception as exe:
            log.error(f'> message sending ERROR: [{str(exe)}]')
        return


if __name__ == '__main__':
    main(**args_parser())
