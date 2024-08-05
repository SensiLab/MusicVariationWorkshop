
from gevent import monkey
monkey.patch_all()

import os
import sys
import time

from celery import Celery
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, redirect
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename


from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required
from flask_bcrypt import Bcrypt

from MusicVariationBert.generation import generate_variations, write_variations, MusicBERTModel
from MusicVariationBert.utils import reverse_label_dict

# from generate_melody import MagentaMusicTransformer

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
VARIATION_FOLDER = "variations"
SOCKETIO_REDIS_URL = 'redis://130.194.71.74/:6379/0'  

# Configure Celery with Redis as the backend
app.config.from_pyfile('celery_config.py')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["VARIATION_FOLDER"] = VARIATION_FOLDER
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, message_queue=SOCKETIO_REDIS_URL)

# Create a Celery instance
celery = Celery(
    app.name,
    broker=app.config['CELERY_BROKER_URL'],
    backend=app.config['CELERY_RESULT_BACKEND']
)
celery.conf.update(app.config)

# login manager
login_manager = LoginManager()
login_manager.init_app(app)
bcrypt = Bcrypt(app)

# database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)


class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f'<User {self.username}>'
    
def new_user(username, password):

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username,password_hash=hashed_password) 
    db.session.add(new_user)
    db.session.commit()

# models
# magenta_transformer = MagentaMusicTransformer("model/melody_conditioned_model_16.ckpt")

roberta_base = MusicBERTModel.from_pretrained('.', 
    checkpoint_file='checkpoints/checkpoint_last_musicbert_base_w_genre_head.pt'
)
roberta_base.eval()

label_dict = roberta_base.task.label_dictionary
reversed_dict = reverse_label_dict(label_dict)

# set temperature
temp = 1 

temp_bar = 1
temp_pos = 1
temp_ins = 1
temp_pitch = 3
temp_dur = 1
temp_vel = 3 
temp_sig = 1
temp_tempo = 1

# create temperature dict
temperature_dict = {
    0 : temp_bar,
    1 : temp_pos,
    2 : temp_ins,
    3 : temp_pitch,
    4 : temp_dur,
    5 : temp_vel,
    6 : temp_sig,
    7 : temp_tempo,
}


# 0: bar | 1: position | 2: instrument | 3: pitch | 4: duration | 5: velocity | 6: time signature | 7: tempo 
attributes = [3, 4]
bars = [(3, 5)]

@celery.task
def generate_variation(input_path, output_filename, jobs, socket_sid, variation_args):
    for i in range(jobs):

        output_path = app.config["VARIATION_FOLDER"] + f'/{i+1}_' + output_filename

        # magenta_transformer.generate(input_path, output_path)
        variations =generate_variations(filename=input_path,
                                        n_var=1,
                                        roberta_base=roberta_base,
                                        label_dict=label_dict,
                                        reversed_dict=reversed_dict,
                                        new_notes=False,
                                        variation_percentage=50,
                                        attributes=attributes,
                                        temperature_dict=temperature_dict,
                                        bars=bars,
                                        bar_level=False)
        
        write_variations(variations, output_path, reversed_dict)

        socketio.emit('job_complete', {'filename': os.path.basename(output_filename), 'job' : (i+1)}, room=socket_sid)
    
    socketio.emit('processing_complete', {'filename': os.path.basename(output_filename)}, room=socket_sid)

# login manager
@login_manager.user_loader
def load_user(user_id):
  return User.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login')

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()

    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        return redirect("/")
  
  return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/login")

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
    bar = request.form.get('bar', type=str)
    position = request.form.get('position', type=str)
    instrument = request.form.get('instrument', type=str)
    pitch = request.form.get('pitch', type=str)
    duration = request.form.get('duration', type=str)
    timesignature = request.form.get('timesignature', type=str)
    tempo = request.form.get('tempo', type=str)

    attributes = [bar, position, instrument, pitch, duration, timesignature, tempo]
    bars = request.form.getlist('numbers[]', type=int)
    barlevel = request.form.get('barlevel', type=str)
    variation_amount = request.form.get('variationamount', type=int)
    newnotes = request.form.get('newnotes', type=str)
    newnotes_amount = request.form.get('newnotesamount', type=int)

    variation_args = {
        "attributes" : attributes,
        "bars" : bars,
        "barlevel" : barlevel,
        "variation_amount" : variation_amount,
        "newnotes" : newnotes,
        "newnotes_amount" : newnotes_amount
    }


    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Add the file and numberOfJobs to the Celery task queue
    generate_variation.apply_async(args=[filepath, file.filename, jobs, sid, variation_args])


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

    with app.app_context():
        db.create_all()
        # new_user("admin", "Bert@Variation")
    
    socketio.run(app, host="0.0.0.0", port=8008, debug=True)



