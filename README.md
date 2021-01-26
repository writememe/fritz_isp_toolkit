![fritz_isp_toolkit](https://github.com/writememe/motherstarter/workflows/fritz_isp_toolkit/badge.svg)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)


# Fritz ISP Router Toolkit

A repository to interface with Fritz ISP routers and send notifications via Gmail

## Introduction

This tool uses the [fritzconnection](https://fritzconnection.readthedocs.io/en/1.4.0/index.html) python module to interface with the Fritz Router so that you can process the device logs off
the device.

From there, you have to option to send an email via the Gmail API. Realistically, you could swap out
the notification to whatever tool you like.

## Preparation

### ISP Router - Environmental Variables

The tool ingests environmental variables for authentication to the Fritz ISP router. These are:

- `ISP_RTR_UNAME` = your_username
- `ISP_RTR_PWORD` = your_password
- `ISP_RTR_ADDRESS` = your_isp_router_ip

The tool will prefer environmental variables in the following order:

1) Any environmental variables set `.env` file, inside the [creds/](creds/) folder.
2) Any other method in which you would like to set the environmental variables by.

### Gmail API - Optional

You will need to follow the [Gmail Python quickstart guide](https://developers.google.com/gmail/api/quickstart/python).  

Then, copy the contents of the `credentials.json` file provided and save to a file
called `credentials_home_automation.json` inside the [creds/](.creds/) folder.

## Installation

In order to use the application, please follow the installation instructions below:

1. Create the virtual environment to run the application in:

```bash
virtualenv --python=`which python3` venv
source venv/bin/activate
```

2. Install the requirements:

```python
pip install -r requirements.txt
```

## Operating Instructions

In order to operate the tool, please perform the following:

```python

python modules/isp_toolkit.py

```

This will output a timestamped log in the [logs](logs/README.md) folder.