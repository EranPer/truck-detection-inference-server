"""
Configuration file for the Waste Reduction project
"""

# How to get video url:
# https://stackoverflow.com/questions/42901942/how-do-we-download-a-blob-url-video/49835269#49835269

# Cameras dictionary
CAMERA = {
    'TEL_ARAD_CAM':
        {
            'ID': '0001',
            'NAME': 'תל ערד',
            'URL': 'https://5e0d15ab12687.streamlock.net/live/TELARAD.stream/chunklist_w1876910744.m3u8'
        },
    'EVLAIM_CAM':
        {
            'ID': '0002',
            'NAME': 'אבליים',
            'URL': 'https://5d8c50e7b358f.streamlock.net/live/EVLAIM.stream/chunklist_w117438879.m3u8'
        },
    'SHAAR_HANEGEV_CAM':
        {
            'ID': '0003',
            'NAME': 'שער הנגב',
            'URL': 'https://5e0d15ab12687.streamlock.net/live/SHAARHANEGEV.stream/chunklist_w956961233.m3u8'
        },
    'ZIKIM_CAM':
        {
            'ID': '0004',
            'NAME': 'זיקים',
            'URL': 'https://5d8c50e7b358f.streamlock.net/live/ZIKIM.stream/chunklist_w853947908.m3u8'
        }
}

# Access key to AWS. Write here your aws credentials
AWS_ACCESS_KEY_ID = None
AWS_SECRET_ACCESS_KEY = None

# S3 bucket name. Write here your s3 bucket name
BUCKET = None

# Path to input data folder
INPUT_FOLDER = 'input_data'

# Path to output data folder
OUTPUT_FOLDER = 'output_data'

# Frame/s option for reading data from INPUT_FOLDER
FETCH = ['last', 'all']

# Truck classes
CLASS_NAME = {0: 'uncovered', 1: 'covered', 2: 'other'}

# Inference threshold
CONF_THRES = 0.25

# Serial max number - 7 digits
MAX_SERIAL_NUM = 9999999

# Backend server's url address to send alerts in a json format
BACKEND_URL = ''

# classapscheduler.triggers.interval.IntervalTrigger
# (weeks=0, days=0, hours=0, minutes=0, seconds=0, start_date=None, end_date=None, timezone=None, jitter=None)

# This method schedules jobs to be run periodically, on selected intervals.

# weeks (int) – number of weeks to wait
# days (int) – number of days to wait
# hours (int) – number of hours to wait
# minutes (int) – number of minutes to wait
# seconds (int) – number of seconds to wait
# start_date (datetime|str) – starting point for the interval calculation
# end_date (datetime|str) – latest possible date/time to trigger on
# timezone (datetime.tzinfo|str) – time zone to use for the date/time calculations
# jitter (int|None) – delay the job execution by jitter seconds at most

# Interval time in seconds between inference for the backend server
INFERENCE_INTERVAL_SECONDS = .5

# Interval time in weeks between cleaning (deleting local data)
CLEANING_INTERVAL_WEEKS = 2

# Interval time in weeks between uploading local data
UPLOADING_INTERVAL_DAYS = 1
