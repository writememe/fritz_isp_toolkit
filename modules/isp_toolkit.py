#!/usr/bin/env python3
"""
Toolkit to manage Fritz Internet Router
to parse it's device logs and send notifications
via Gmail.

You can use something else to send the Gmail notification.
"""
# Import modules
import os
import sys
from os import environ
from fritzconnection import FritzConnection
import pathlib as pl
import datetime as dt
import os.path
from dotenv import load_dotenv
import pathlib
import yagmail
from typing import List


print("Commencing ISP Toolkit ...")
# Get path of the current dir under which the file is executed
dirname = os.path.dirname(os.path.abspath(__file__))
# Append sys path so that relative pathing works for input
# files and templates
sys.path.append(os.path.join(dirname))

# Setup credential_dir
CRED_DIR = pathlib.Path.cwd().joinpath(dirname, "..", "creds")

"""
Block of code to process the ingestion of environmental
variables
"""
# Get path to where environmental variables are stored and
env_path = pathlib.Path.cwd().joinpath(CRED_DIR, ".env")
# NOTE: This has been set to always revert to system provided environmental
# variables, rather than what is provided in the .env file using
# the override=False method.
# If nothing is set on the system, the values from the .env file are used.
load_dotenv(dotenv_path=env_path, override=True)
# Specify todays and yesterdays date as global variables
TODAY = dt.datetime.today()
YESTERDAY = TODAY - dt.timedelta(days=1)

# Specify a list of environmental variables
# for usage inside script
environment_variables = [
    "ISP_RTR_UNAME",
    "ISP_RTR_PWORD",
    "ISP_RTR_ADDRESS",
    "GMAIL_ACC",
    "GMAIL_PWORD",
]
# Iterate over environmental variables and ensure they are set,
# if not exit the program.
for variables in environment_variables:
    if environ.get(variables) is not None:
        print(f"Environmental variable: {variables} is set.")
    else:
        print(f"Environmental variable: {variables} is NOT set, exiting script.")
        sys.exit(1)

# Assign environmental variables to variables for usage.
isp_uname = environ.get("ISP_RTR_UNAME")
isp_pword = environ.get("ISP_RTR_PWORD")
isp_address = environ.get("ISP_RTR_ADDRESS")
gmail_acc = environ.get("GMAIL_ACC")
gmail_pword = environ.get("GMAIL_PWORD")


def get_timestamp() -> str:
    """
    Get the current time and convert into a timestamp for
    further usage

    Args:
        N/A

    Raises:
        N/A

    Returns:
        timestamp: A timestamp string for further usage.
    """
    # Capture time
    cur_time = dt.datetime.now()
    return cur_time.strftime("%Y-%m-%d-%H-%M-%S")


def create_log_dir(log_dir: str = "logs"):
    """
    Create log directory to store outputs.

    Args:
        log_dir: The name of the directory to be created.
            Default: "logs:

    Raises:
        N/A

    Returns:
        log_dir: The log directory for further usage.
    """
    # Create entry directory and/or check that it exists
    pl.Path(log_dir).mkdir(parents=True, exist_ok=True)
    return log_dir


def initialise_connection(isp_address: str, isp_uname: str, isp_pword: str):
    """
    Initialise connection to the Fritz ISP router.
    Args:
        isp_address: The ISP router address.
        isp_uname: The ISP router username.
        isp_pword: The ISP router password.

    Raises:
        N/A

    Returns:
        fc: An initialised connection to the Fritz ISP router.
    """
    # Informational printout
    print(f"Initialising connection to: {isp_address}")
    # Initialise connection to Fritz Routers
    fc = FritzConnection(address=isp_address, user=isp_uname, password=isp_pword)
    return fc


def retrieve_logs(fc):
    """
    Retrieve the logs from the Fritz ISP router in dictionary format.

    Args:
        fc: An initialised connection to the Fritz ISP router.
    Raises:
        N/A
    Returns:
        logs (dict): A single key/value dictionary containing the logs.
            Example:
                 {
                     'NewDeviceLog': 'log1date log1subject: log1detail\n log2date log2subject: log12detail'
                 }
    """
    # Retrieve the raw logs from the Fritz ISP Router
    logs = fc.call_action("DeviceInfo:1", "GetDeviceLog")
    return logs


def process_logs(logs: dict) -> List:
    """
    Take the dictionary containing the log
    entries and parse them to reformat the output
    into a more human readable list of logs.

    Args:
    logs (dict): A single key/value dictionary containing the logs.
        Example:
                {
                    'NewDeviceLog': 'log1date log1subject: log1detail\n log2date log2subject: log12detail'
                }

    Raises:
        N/A

    Returns:
        log_list: A list of logs
    """
    # Grab the single value out of the dictionary, put it through
    # a list, then string it so we can work with it
    # NOTE: This isn't great.
    log_data = str(list(logs.values()))
    log_data = log_data.lstrip("['").rstrip("']")
    # Each log entry is seperated by a newline character
    # so we split on this to get the list of logs.
    log_list = log_data.split("\\n")
    # Debug print
    print(f"Total logs discovered: {len(log_list)}")
    return log_list


def process_log_entry(log_entry):
    # Set alert boolean to False by default
    alert = False
    # Define a list of strings which indicate alerts of concern, and
    # not the usual "noise" of Wireless alerts
    alert_strings = [
        "Internet connection established successfully. IP address:",  # Indicates that Internet re-established
        "PPPoE error:",  # PPPoE issues
    ]
    # Check if any of the log strings contain the alert substrings. This validates the the log
    # entry has an alert string of interest in it.
    if any(substring in log_entry for substring in alert_strings):
        # NOTE: We are stripping the timestamp and converting to a datetime
        # object for comparison
        # '25.09.21 06:38:09 <some log message>'
        log_entry_time_string = log_entry[:17]
        log_entry_timestamp = dt.datetime.strptime(
            log_entry_time_string, "%d.%m.%y %H:%M:%S"
        )
        # If the log entry date, is also greater than yesterdays time, this means it's a "new alert"
        # and we are interesting in knowing this alert
        if log_entry_timestamp > YESTERDAY:
            # Set the alert boolean to True, so it can be used outside this function.
            alert = True
    return alert


# Gmail notification block


def authorise_yagmail_client(
    gmail_acc: str = gmail_acc, gmail_pword: str = gmail_pword
):
    """
    Instantiate a connection to the yagmail client
    and return for use in other functions.

    Args:
        gmail_acc: The Gmail username used to login to your account.
        gmail_pword: The Gmail password used to login to your account.

    Raises:
        N/A

    Returns:
        yg: An instantiated object, ready for sending emails.
    """
    yg = yagmail.SMTP(gmail_acc, gmail_pword)
    return yg


def process_isp_logs():
    """
    Function to join together multiple operations
    related to the Fritz ISP Router portion of the
    script.

    Args:
        N/A

    Raises:
        N/A

    Returns:
        log_file: The log_file containing the Fritz ISP router
        logs, ready for further processing.
        timestamp: A string formatted timestamp for usage for the
        notification component of the main workflow.
        alert: A boolean which indicates that there was an event worthy of sending an alert

    """
    # Instantiate an alert counter, this will be incremented
    # if there is an event of interest
    alert_counter = 0
    # Get timestamp and assign to a variable.
    timestamp = get_timestamp()
    # Create a logs directory to save the results into.
    log_dir = os.path.join(dirname, "..", "logs")
    output_dir = create_log_dir(log_dir=log_dir)
    # Initialise connection to Fritz ISP Router
    fc = initialise_connection(isp_address, isp_uname, isp_pword)
    # Retrieve and parse logs from Fritz ISP Router
    logs = retrieve_logs(fc)
    log_list = process_logs(logs)
    # Auto-generate log_file variable, using timestamp and output_dir
    log_file = f"{output_dir}/{timestamp}-log-stats.txt"
    # Open file for writing
    with open(f"{log_file}", "w") as summary_log_file:
        # Iterate over log_entries in log_list
        for log_entry in log_list:
            # Right-strip and left-strip any trailing string
            # elements left from the original dictionary.
            # NOTE: This isn't great, but works.
            log_entry = log_entry.lstrip("['").rstrip("']")
            # Process log entry for interesting alert
            alert_result = process_log_entry(log_entry)
            # If an interesting log alert is found, increment the counter
            if alert_result:
                alert_counter += 1
            # Write the log entry to the file.
            summary_log_file.write(log_entry + "\n")
    # If the alert
    alert = alert_counter > 0
    print(f"ALERT: {alert}")
    return log_file, timestamp, alert


# Main workflow


def main(yagmail=True):
    """
    Main workflow for the application.
    """
    # Connect to Fritz ISP Router and process the logs
    data = process_isp_logs()
    # Assign the log_file returned from the tuple to a variable
    log_file = data[0]
    # Assign the timestamp returned from the tuple to a variable
    timestamp = data[1]
    # Assign the alert boolean from the tuple to a variable
    alert = data[2]
    if yagmail and alert:
        # Initialise the yagmail client so we can send the email
        yag = authorise_yagmail_client(gmail_acc, gmail_pword)
        # Create list of files to be attached to email
        file_list = [log_file]
        email_body = f"Attached is the log file {log_file}."
        # Send the email
        email_result = yag.send(
            to="danielfjteycheney@gmail.com",
            subject=f"ISP Log File Report - {timestamp}",
            contents=[email_body],
            attachments=file_list,
        )
        print(f"Result of email: {email_result}")
    else:
        print("Logs parsed, no new alerts")


if __name__ == "__main__":
    main()
