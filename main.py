
import os
import time

from celery import Celery
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
VARIATION_FOLDER = "variations"
SOCKETIO_REDIS_URL = 'redis://localhost:6379/0'  

# Configure Celery with Redis as the backend
app.config.from_pyfile('celery_config.py')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["VARIATION_FOLDER"] = VARIATION_FOLDER
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app,message_queue=SOCKETIO_REDIS_URL)

# Create a Celery instance
celery = Celery(
    app.name,
    broker=app.config['CELERY_BROKER_URL'],
    backend=app.config['CELERY_RESULT_BACKEND']
)
celery.conf.update(app.config)

@celery.task
def generate_variation(input_path, output_filename, jobs, socket_sid):
    for i in range(jobs):
        time.sleep(2)
        output_path = app.config["VARIATION_FOLDER"] + f'/{i+1}_' + output_filename
        with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
            outfile.write(infile.read())

        socketio.emit('job_complete', {'filename': os.path.basename(output_filename), 'job' : (i+1)}, room=socket_sid)
    
    socketio.emit('processing_complete', {'filename': os.path.basename(output_filename)}, room=socket_sid)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():

    sid = request.args.get('sid')

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Get the numberOfJobs value from the form data
    jobs = request.form.get('jobs', type=int)

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Add the file and numberOfJobs to the Celery task queue
    generate_variation.apply_async(args=[filepath, file.filename, jobs, sid])


    # Send a JSON response to the client
    response_data = {'message': 'File added to processing queue', 'filename': filename}

    return jsonify(response_data)

@app.route('/variations/<filename>')
def download_file(filename):
    return send_from_directory(app.config['VARIATION_FOLDER'], filename, as_attachment=True)


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

if __name__=="__main__":
    socketio.run(app, host="127.0.0.1", port=8080, debug=True)

