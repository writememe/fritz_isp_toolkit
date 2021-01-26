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
from apiclient import errors


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
# NOTE: If modifying these scopes, delete the file token.pickle
# from within the CRED_DIR directory
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
    # Each log entry is seperated by a newline character
    # so we split on this to get the list of logs.
    log_list = log_data.split("\\n")
    # Debug print
    print(f"Final log list: {log_list}")
    return log_list


# Gmail notification block

def authorise_gmail_service():
    """
    Authorise and establish connection
    to the Gmail service so that operations
    can be performed against the Gmail API.


    Args:
        N/A

    Raises:
        N/A

    Returns:
        service: An established object with
        access to the Gmail API

    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(os.path.join(CRED_DIR, "token.pickle")):
        with open(os.path.join(CRED_DIR, "token.pickle"), "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    # to generate more credentials.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(CRED_DIR, "credentials_home_automation.json"), SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run into the CRED_DIR
        with open(os.path.join(CRED_DIR, "token.pickle"), "wb") as token:
            pickle.dump(creds, token)
    # Create the resource which will be used against the Gmail API
    service = build("gmail", "v1", credentials=creds)
    return service


def create_email_with_attachment(to, subject, message_text, file_list):
    """
    Send an email using the Gmail API with one or more attachments.

    Args:
        to: The to recipient of the email.
            Example: johndoe@gmail.com
        subject: The subject of the email.
        service: An established object with authorised access to the Gmail API
        for sending emails.
        message_text: The body of the message to be sent.
        file_list: A list of files to be attached to the email.
    
    Raises:
        N/A

    Returns:
        message: A message in the proper format, ready to be sent
        by the send_email function.
    """

    # Create an email message
    mimeMessage = MIMEMultipart()
    mimeMessage["to"] = to
    mimeMessage["subject"] = subject
    mimeMessage.attach(MIMEText(message_text, "plain"))

    # Attach files from the list of files
    for attachment in file_list:
        content_type, encoding = mimetypes.guess_type(attachment)
        main_type, sub_type = content_type.split("/", 1)
        file_name = os.path.basename(attachment)
        f = open(attachment, "rb")
        my_file = MIMEBase(main_type, sub_type)
        my_file.set_payload(f.read())
        my_file.add_header("Content-Disposition", "attachment", filename=file_name)
        encoders.encode_base64(my_file)
        f.close()
        mimeMessage.attach(my_file)

    # Format message dictionary, ready for sending
    message = {"raw": base64.urlsafe_b64encode(mimeMessage.as_bytes()).decode()}
    return message



def send_message(service, user_id, message):
    """
    Send an email message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        message: Message to be sent.

    Returns:
        Sent Message.
    """
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        message_id = message["id"]
        print(f"Message Sent - Message ID: {message_id}")
        return message
    except errors.HttpError as err:
        print(f"An error occurred: {err}")


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

    """
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
    log_file = f"{output_dir}/{timestamp}-log_stats.txt"
    # Open file for writing
    with open(f"{log_file}", "w") as summary_log_file:
        # Iterate over log_entries in log_list
        for log_entry in log_list:
            # Right-strip and left-strip any trailing string
            # elements left from the original dictionary.
            # NOTE: This isn't great, but works.
            log_entry = log_entry.lstrip("['").rstrip("']")
            # Write the log entry to the file.
            summary_log_file.write(log_entry + "\n")
    return log_file, timestamp


# Main workflow

def main(gmail=True):
    """
    Main workflow of the script.

    NOTE: Gmail is used as the "notification" engine,
    but there is nothing stopping you using something else.

    Args:
        gmail: Boolean to toggle gmail notification on/off
    """
    # Connect to Fritz ISP Router and process the logs
    data = process_isp_logs()
    # Assign the log_file returned from the tuple to a variable
    log_file = data[0]
    # Assign the timestamp returned from the tuple to a variable
    timestamp = data[1]
    # If gmail is enabled, send email using gmail with an attachment
    if gmail:
        # Create list of files to be attached to email
        file_list = [log_file]
        # Authorise to the gmail service
        service = authorise_gmail_service()
        # Create email with attachment function
        message = create_email_with_attachment(
            to="danielfjteycheney@gmail.com",
            subject=f"ISP Log File Report - {timestamp}",
            message_text=f"Attached is the log file {log_file}.",
            file_list=file_list,
        )
        # Send the email
        send_message(service=service, user_id="me", message=message)


if __name__ == "__main__":
    main()

