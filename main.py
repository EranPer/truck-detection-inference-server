from config import *
from files import *
from scraper import *
from model import *

from flask import Flask, request
from flask_apscheduler import APScheduler

import json
import time

# create app
app = Flask(__name__, static_folder=OUTPUT_FOLDER)

# Create local data folders
Files(INPUT_FOLDER).create_folder()
Files(OUTPUT_FOLDER).create_folder()

# Setup logger
logger = Files('waste_reduction.log').set_logger()

# Setup s3 client
s3 = Files(s3_bucket=BUCKET, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# Scraper instance
s = Scraper(CAMERA['TEL_ARAD_CAM'], MAX_SERIAL_NUM)

# Continue counter from last serial number
s.reset_counter(len(os.listdir(INPUT_FOLDER)))

# Model instance
m = Model('best.pt')

# Initialize scheduler
scheduler = APScheduler()

# Start scheduler
scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()

logger.info('Starting server')


@app.route('/')
def index():
    """
    :return: Html webpage for viewing the current frame or the requested frame (?id=img00010000000_DD_MM_YYYYTHH_MM_SS)
    """
    image_id = request.args.get('id')
    if image_id is not None:
        # for requested image ID
        output = {'image_id': image_id}
        logger.info('api-get-index: viewing frame ' + image_id + '.jpg from local data')
    else:
        # infer new frame
        output = inference(m)
        logger.info('api-get-index: inferring and viewing new frame ' + str(output))
    html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Truck Class Detection</title>
            </head>
            <body>
            <h1>
                Welcome to Truck Class Detection Model<br>
            </h1>
            '''
    if output is not None:
        # show output
        html += '<br><img src="'
        html += OUTPUT_FOLDER + '/' + output['image_id'] + '.jpg'
        html += '" alt="current frame"><br><b>'
        html += str(output['image_id'])
    else:
        # No valid output
        html += 'No input data to infer. Please check local data.'
        html += '''
            </b>  
            </body>
            </html>
            '''
    return html


def fetch_data(
        scraper=None,
        bucket_name=None,
        subfolder=INPUT_FOLDER,
        fetch='last'):
    """
    Fetching a frame or a list of frames from a local or remote (s3) input folder and saving locally.
    :param: scraper: the scraper instance.
    :param: bucket_name: the s3 bucket name.
    :param: subfolder: the folder which the input data is stored.
    :return: path and name of the frame.
    """
    # scrape frame into the local folder
    if scraper is not None:
        frame = scraper.scrape(subfolder)

    # download last frame from s3 bucket into the local folder
    elif bucket_name is not None:
        s3.download_from_s3_to_local(subfolder)

    # fetch last frame or all frames from the local folder
    else:
        files = [subfolder + '/' + f for f in os.listdir(subfolder)]

        if len(files) == 0:
            print('There are no files inside', subfolder)
            return None
        elif fetch == 'last':
            frame = files[-1]
        else:
            frame = files

    return frame


def inference(model=m,
              bucket_name=None,
              subfolder=OUTPUT_FOLDER):
    """
    Fetching input frame and inferring with the model. Saving output data locally.
    :param: model: the model instance.
    :param: bucket_name: the s3 bucket name.
    :param: subfolder: the folder for the output data to be stored in.
    :return: detection output in dictionary format.
    """
    curr = time.time()
    logger.info('Fetching data')
    # fetch frame
    frame = fetch_data(scraper=s)
    if frame is None:
        output = None
    else:
        logger.info('Running model')
        # run the model with the input frame and with the confidence threshold. Saving results in output folder
        output = model.run(source=frame, conf_thres=CONF_THRES, name=subfolder)

    # check if output is valid
    if output is not None:
        # a detection was made
        if not output['detection_results'] == 'no_detections':
            # Replace class number with class name
            output['detection_results']['classes'] = [CLASS_NAME[item] for item in output['detection_results']['classes']]

            # upload label to bucket if bucket exists
            if bucket_name is not None:
                s3.upload_to_s3_from_local(subfolder + '/' + 'labels' + '/' + output['image_id'] + '.txt')

        # upload image to bucket if bucket exists
        if bucket_name is not None:
            s3.upload_to_s3_from_local(subfolder + '/' + output['image_id'] + '.jpg')

        # print the inference time
        inference_time = str(time.time() - curr)
        print('inference time is ' + inference_time + ' seconds')
        logger.info('inference time is ' + inference_time + ' seconds')

    return output


@app.route("/detect_trucks", methods=["GET"])
def detect_trucks():
    """
    REST API GET for an inference.
    :return: detection output in json format.
    """
    output = inference()
    logger.info('api-get-detect_trucks: ' + str(output))
    return json.dumps(output), 200


# To enable scheduler, uncomment the next line
# @scheduler.task('interval', id='inference_post', seconds=INFERENCE_INTERVAL_SECONDS)
def inference_post():
    """
    REST API POST for an inference.
    """
    output = inference()
    # a detection was made
    if output is not None:
        if not output['detection_results'] == 'no_detections':
            print('truck detected')
            # Send the detection data to the backend server
            x = requests.post(BACKEND_URL, json=output)
            print(x.text)
    logger.info('api-post: ' + str(output))
    print(output)


@app.route("/send_local_data_list", methods=["GET"])
def send_local_data_list():
    """
    REST API GET for sending local list of files in output folder to the client.
    """
    files = os.listdir(OUTPUT_FOLDER)
    # no files in the output folder
    if len(files) == 0:
        frames = labels = []
    # at least 1 file the in output folder
    else:
        frames = files[:-1]
        labels = ['labels/' + label for label in os.listdir(OUTPUT_FOLDER + '/' + 'labels')]

    logger.info('api-get-send_local_data_list')
    return json.dumps('{files: {frames: ' + str(frames) + ', labels: ' + str(labels) + '}'), 200


# REST GET action
@app.route("/upload_local_data_to_s3", methods=["GET"])
# To enable scheduler, uncomment the next line and comment the upper line
# @scheduler.task('interval', id='upload_local_data_to_s3', days=UPLOADING_INTERVAL_DAYS)
def upload_local_data_to_s3():
    """
    REST API GET for uploading local output data to s3 bucket.
    Can be a specific file (?file=img00010000023_20_11_2022T02_54_24.jpg, for example) or all files in the output folder
    """
    # no bucket. return error message
    if BUCKET is None:
        return json.dumps('No bucket'), 200

    filename = request.args.get('file')
    # filename as argument
    if filename is not None:
        try:
            # filename is valid. uploading it
            s3.upload_to_s3_from_local(OUTPUT_FOLDER + '/' + filename)
            logger.info('Uploaded local file to s3 bucket: ' + filename)
            return json.dumps('{uploaded: {filename: ' + filename + '}}'), 200
        except:
            # filename is invalid. return error message
            return json.dumps('{No such file ' + filename + '}'), 200
    else:
        files = os.listdir(OUTPUT_FOLDER)
        # no files in the output folder
        if len(files) == 0:
            return json.dumps('{No files in local output folder}'), 200
        # at least 1 file the in output folder
        else:
            # uploading all frames
            frames = files[:-1]
            for idx, frame in enumerate(frames):
                print(idx + 1, '/', len(frames), 'uploading', frame)
                s3.upload_to_s3_from_local(OUTPUT_FOLDER + '/' + frame)

            # uploading all labels
            labels = os.listdir(OUTPUT_FOLDER + '/' + 'labels')
            for idx, label in enumerate(labels):
                print(idx + 1, '/', len(labels), 'uploading', label)
                s3.upload_to_s3_from_local(OUTPUT_FOLDER + '/' + 'labels' + '/' + label)

            logger.info('Uploaded all local output files to s3 bucket')

    logger.info('api-get-upload_local_data_to_s3')

    return json.dumps('{uploaded: {frames: ' + str(frames) + ', labels: ' + str(labels) + '}}'), 200


# REST GET action
@app.route("/delete_local_data", methods=["GET"])
# To enable scheduler, uncomment the next line and comment the upper line
# @scheduler.task('interval', id='delete_local_data', weeks=CLEANING_INTERVAL_WEEKS)
def delete_local_data():
    """
    REST API GET for deleting local output data.
    Deleting old input and output folders.
    Creating new input and output folders.
    Resetting counter to 0.
    """
    # Remove local folders and files
    Files(INPUT_FOLDER).delete_folder()
    Files(OUTPUT_FOLDER).delete_folder()
    time.sleep(0.5)

    # Create local data folders
    Files(INPUT_FOLDER).create_folder()
    Files(OUTPUT_FOLDER).create_folder()

    time.sleep(0.5)
    s.reset_counter()

    logger.info('Deleted local data')

    return json.dumps('{deleted: [' + INPUT_FOLDER + ', ' + OUTPUT_FOLDER + ']}'), 200


def main():
    app.run(host='0.0.0.0', port=80)


if __name__ == '__main__':
    main()
