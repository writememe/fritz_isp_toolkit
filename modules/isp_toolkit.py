#!/usr/bin/env python3
"""
Toolkit to manage Fritz Internet Router
"""
# Import modules
import os
import sys
from os import environ
from fritzconnection import FritzConnection
import pathlib as pl
import datetime as dt
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import mimetypes
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dotenv import load_dotenv
import pathlib


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

# Specify a list of environmental variables
# for usage inside script
environment_variables = [
    "ISP_RTR_UNAME",
    "ISP_RTR_PWORD",
    "ISP_RTR_ADDRESS",
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

# Gmail API scopes
# NOTE: If modifying these scopes, delete the file token.pickle from within the CRED_DIR
# directory
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",  # Only need this scope to send email
]


def get_timestamp():
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
    # Cleanup time, so that the format is clean for the output file 2019-07-01-13-04-59
    timestamp = cur_time.strftime("%Y-%m-%d-%H-%M-%S")
    return timestamp


def create_log_dir(log_dir="logs"):
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


def process_logs(logs):
    """"""
    # Grab the value out of the dictionary
    log_data = str(list(logs.values()))
    for item in logs.items():
        print(str(item) + "\n")
    print(f"LOG DATA: {log_data}")
    print(type(log_data))
    log_list = log_data.split("\\n")
    print("*" * 50)
    print(log_list)
    print("*" * 50)
    for item in log_list:
        print(f"Log Entry: {item}")
    print(type(log_list))
    return log_list


# Gmail notification


def build_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials_home_automation.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("gmail", "v1", credentials=creds)
    return service


def send_email_with_attachment(sender, to, subject, service, message_text, file_list):
    """
    Working function, leave as is
    """

    # create email message
    mimeMessage = MIMEMultipart()
    mimeMessage["to"] = to
    mimeMessage["subject"] = subject
    mimeMessage.attach(MIMEText(message_text, "plain"))

    # Attach files
    for attachment in file_list:
        content_type, encoding = mimetypes.guess_type(attachment)
        main_type, sub_type = content_type.split("/", 1)
        file_name = os.path.basename(attachment)
        f = open(attachment, "rb")
        myFile = MIMEBase(main_type, sub_type)
        myFile.set_payload(f.read())
        myFile.add_header("Content-Disposition", "attachment", filename=file_name)
        encoders.encode_base64(myFile)
        f.close()
        mimeMessage.attach(myFile)

    raw_string = base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()
    message = (
        service.users().messages().send(userId="me", body={"raw": raw_string}).execute()
    )
    print(message)


def process_isp_logs():
    timestamp = get_timestamp()
    output_dir = create_log_dir(log_dir="logs")
    fc = initialise_connection(isp_address, isp_uname, isp_pword)
    logs = retrieve_logs(fc)
    log_list = process_logs(logs)
    sum_log_file_name = f"{output_dir}/{timestamp}-log_stats.txt"
    with open(f"{sum_log_file_name}", "w") as s_log_file:
        for line in log_list:
            line = line.lstrip("['").rstrip("']")
            s_log_file.write(line + "\n")
    return sum_log_file_name, timestamp


def main():
    data = process_isp_logs()
    log_file = data[0]
    timestamp = data[1]
    file_list = [log_file]
    message_body = f"Attached is the log file {log_file}."
    # service = build_gmail_service()
    # # Working send email with attachment function
    # email = send_email_with_attachment(
    #     sender="danielfjteycheney@gmail.com",
    #     to="danielfjteycheney@gmail.com",
    #     subject=f"ISP Log File Report - {timestamp}",
    #     service=service,
    #     message_text=message_body,
    #     file_list=file_list,
    # )
    # print(email)


main()


# fc = FritzConnection(address="192.168.178.1", user=isp_uname, password=isp_pword)
# state = fc.call_action("WLANConfiguration1", "GetInfo")
# print(state)
# something = fc.call_action("DeviceInfo:1", "GetDeviceLog")
# for key, value in something.items():
#     print(f"Key: {key}")
#     print(f"Value: {value}")
#     print("*" * 50)


# something_44 = fc.call_action("DeviceInfo:1", "GetInfo")
# for key, value in something_44.items():
#     print("something_55")
#     print(f"Key: {key}")
#     print(f"Value: {value}")
#     print("*" * 50)


# something_2 = fc.call_action("WANPPPConnection1", "GetStatusInfo")
# for key, value in something_2.items():
#     print(f"Key: {key}")
#     print(f"Value: {value}")
#     print("*" * 50)

# something_23 = fc.call_action("WANIPConn1", "GetStatusInfo")
# for key, value in something_23.items():
#     print(f"Key: {key}")
#     print(f"Value: {value}")
#     print("*" * 50)
# print(something)
