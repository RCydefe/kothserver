import requests
import re
from flask import Flask, render_template, Response
from threading import Thread, Timer
from datetime import datetime
import traceback
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.dates import DayLocator, HourLocator
from io import BytesIO
import matplotlib.dates as mdates
import json
import time

app = Flask(__name__)

scoreboard = {}
targets = []
token_history = {}

SCORES_FILE = 'scoresbak.txt'
TARGETS_FILE = 'targets.txt'
HISTORY_FILE = 'history.json'


def load_scores():
    global scoreboard
    try:
        with open(SCORES_FILE, 'r') as file:
            for line in file:
                token, score = line.strip().split(': ')
                scoreboard[token] = int(score)
    except FileNotFoundError:
        pass

def save_scores():
    with open(SCORES_FILE, 'w') as file:
        for token, score in scoreboard.items():
            file.write(f"{token}: {score}\n")

def load_targets_thread():
    while True:
        load_targets()
        for target in targets:
            thread = Thread(target=update_score_thread, args=[target])
            thread.daemon = True
            thread.start()
        # Adjust the sleep time to control the interval between target reloads
        time.sleep(15)  # Wait for 5 minutes before reloading targets

def load_targets():
    global targets
    targets = []
    try:
        with open(TARGETS_FILE, 'r') as file:
            for line in file:
                url = line.strip()
                targets.append({'url': url, 'token': ''})
    except FileNotFoundError:
        pass

def load_history():
    global token_history
    try:
        with open(HISTORY_FILE, 'r') as file:
            token_history = json.load(file)
            for token, history in token_history.items():
                token_history[token] = [(datetime.fromisoformat(time), score) for time, score in history]
    except FileNotFoundError:
        pass

def save_history():
    with open(HISTORY_FILE, 'w') as file:
        serialized_history = {token: [(time.isoformat(), score) for time, score in history] for token, history in token_history.items()}
        json.dump(serialized_history, file)

def update_score(target):
    global scoreboard, token_history
    url = target['url']
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.text
        m = re.search(r'Token:\s*(\d{10})', data)
        if m:
            token = m.group(1)
            target['token'] = token
            if token in scoreboard:
                scoreboard[token] += 10
            else:
                scoreboard[token] = 10

            if token in token_history:
                token_history[token].append((datetime.now(), scoreboard.get(token, 0)))
            else:
                token_history[token] = [(datetime.now(), scoreboard.get(token, 0))]
    except (requests.exceptions.RequestException, ConnectionError) as e:
        print(f"Error retrieving data from {url}: {e}")
        target['token'] = 'N/A'
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

def update_score_thread(target):
    update_score(target)
    t = Timer(10.0, update_score_thread, args=[target])
    t.daemon = True
    t.start()

def periodic_save():
    save_scores()
    save_history()
    t = Timer(10.0, periodic_save)
    t.daemon = True
    t.start()

@app.route('/')
def index():
    return render_template('scoreboard.html', scoreboard=scoreboard, targets=targets, score_graph='/plot')

@app.route('/plot')
def plot():
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)

    min_time = datetime.now()
    max_time = datetime.now()

    for token, history in token_history.items():
        times, scores = zip(*history)
        ax.plot(times, scores, label=token)

        if len(times) > 0:
            min_time = min(min_time, min(times))
            max_time = max(max_time, max(times))

    duration = max_time - min_time

    if duration.days > 1:
        ax.xaxis.set_major_locator(DayLocator())
    elif duration.seconds > 3600:
        ax.xaxis.set_major_locator(HourLocator())
    else:
        ax.xaxis.set_major_locator(mdates.MinuteLocator())

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))

    fig.autofmt_xdate()
    ax.legend()

    canvas = FigureCanvas(fig)
    output = BytesIO()
    canvas.print_png(output)
    response = Response(output.getvalue(), mimetype='image/png')

    return response

if __name__ == '__main__':
    load_scores()
    targets_thread = Thread(target=load_targets_thread)
    targets_thread.daemon = True
    targets_thread.start()
    load_history()
    for target in targets:
        thread = Thread(target=update_score_thread, args=[target])
        thread.daemon = True
        thread.start()

    periodic_save()

    app.run(debug=True, port=8080)
