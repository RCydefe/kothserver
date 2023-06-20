import logging
import yaml
import json
import threading
import requests
import random
import re
from os.path import exists
from time import sleep
from flask import Flask, render_template, flash, request

# Setup Flask
app = Flask(__name__)

# For logging purposes
logger = logging.getLogger("scoreboard")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)
fh = logging.FileHandler("./scoreboard.log")
fh.setFormatter(formatter)
logger.addHandler(fh)
# Change later to INFO instead of DEBUG cause no one needs all your garbage notes!
logger.setLevel('DEBUG')

# Global Magic Stuff Here
user_information = {}
targets = {}

# Reads in the configuration file settings
def read_yaml():   
    if exists('./settings.yaml'):
        with open('./settings.yaml', mode='r') as file:
            try:
                config = yaml.safe_load(file)
                logger.info('Successfully read configuration file.')
                logger.debug(config)
                return config
                
            except yaml.YAMLError as e:
                logger.error(f'Error in settings.yaml file: {e}')
    else:
        logger.error('Unable to find required file: "settings.yaml"')
        exit(1)
        
def safety_checks(conf):
    # Checks to ensure files exists, creates files as needed.
    logger.debug('Performing safety checks...')
    targets_file = conf['targets_file']
    scores_file = conf['scores_file']
    
    if not exists(targets_file):
        logger.error(f'Unable to read the targets file, please make sure the file exists: {targets_file}')
        exit(1)   
    # Scores file
    if not exists(scores_file):
        logger.warning(f'Scores file does not exist, a new scores file will be created: {scores_file}')
    elif exists(scores_file):
        logger.warning(f'Scores file exists, starting server with previous scores: {scores_file}')
        read_scores(conf['scores_file'])
    
    logger.info('Successfully found required files!')  

# Reads the previously saved score file
def read_scores(score_file):
    global user_information
    try:
        with open(score_file, mode='r') as f:
            user_information = json.load(f)
        f.close()
        logger.debug(user_information)
    except Exception as e:
        logger.error(f'Unable to load in the previous score file "{score_file}": {e}')

# Constantly updates the targets file every tgt_sleep seconds.
def read_targets(tgt_file, tgt_sleep):
    global targets
    while True:
        try:
            with open(tgt_file, mode='r') as targets_file:
                for line in targets_file:
                    target = line.strip()
                    if target not in targets.keys():
                        targets[target] = ''
            targets_file.close()
            logger.debug(targets)
            logger.info(f'Successfully updated targets, sleeping for {tgt_sleep} seconds.')
        except Exception as e:
            logger.error(f'Failed to update targets list: {e} - retrying again in {tgt_sleep}')
        sleep(tgt_sleep)

# Saves the scores off periodically 
def save_scores(score_file, periodic_saves):
    global user_information
    while True:
        try:
            logger.info(f'Saving scores file: {score_file}')
            with open(score_file, mode='w') as f:
                json.dump(user_information, f, indent=4)
            f.close()
            logger.info('Successfully saved off scores')
        except Exception as e:
            logger.error(f'Failed to save scores: {e} - retrying again in {periodic_saves}')
        sleep(periodic_saves)    

def query_for_tokens(token_timer):
    global targets
    global user_information
    while True:
        logger.info(f'Grabbing tokens from targets.')
        for target in targets.keys():
            try:
                if 'http://' in target:
                    response = requests.get(target)
                else:
                    response = requests.get('http://' + target)
                tokens_found = re.search(r'[tT][oO][kK][eE][nN]:\s*(\d{10})', response.text)
                if tokens_found:
                    token = tokens_found.group(1)
                    if token in user_information.keys():
                        logger.debug(f'Found token: {token} - on target {target}')
                        targets[target] = token
                        logger.debug(targets)
                    else:
                        targets[target] = ''
                else:
                    targets[target] = ''
            except Exception as e:
                logger.error(f'Unable to get token information from "{target}" - is it alive?...')
                targets[target] = ''
        logger.info(f'Successfully grabbed tokens, will check again in {token_timer} seconds.')
        logger.info(targets)
        sleep(token_timer)

def score_users(score_timer, points):
    while True:
        for target, token in targets.items():
            try:
                user_information[token]['score'] += points  
                user = user_information[token]['username']
                logger.info(f'User {user} scored {points} points!')
            except Exception as e:
                logger.debug(f'Box has been claimed yet {target}: {e}')
        sleep(score_timer)

def rand_token():
    uniq_token = random.randint(0000000000, 9999999999)
    while uniq_token in user_information.keys():
        uniq_token = random.randint(0000000000, 9999999999)
    return uniq_token

def register_user(username):
    global user_information
    score_file = conf['scores_file']
    token = rand_token()
    username = username.lower().title()
    try:
        if any(username in d.values() for d in user_information.values()):
            logger.error(f'User has already been registered: {username}')
            return True
        else:
            user_information[token] = {'username': username, 'score': 0}
            logger.info(f'Successfully registered user: {username}')
            try:
                logger.info(f'Saving scores file: {score_file}')
                with open(score_file, mode='w') as f:
                    json.dump(user_information, f, indent=4)
                f.close()
                logger.info('Successfully saved off scores')
            except Exception as e:
                logger.error(f'Failed to save scores: {e}')
            return False
    except Exception as e:
        logger.error(f'Unable to register user - {username} - Reason: {e}')
        return True

# Website Routing Magic
@app.route("/", methods=['GET'])
def index():
    title = conf['ctf_name']
    target_data = []
    user_scores_data = []
    # Grab target to user information
    for target, token in targets.items():
        if token != '':
            user = user_information[token]['username']
            target_info = f'<tr><td>{target}</td><td><font color="#08c6ab">{user}</font></td></tr>'
        else:
            target_info = f'<tr><td>{target}</td><td><i><font color="#726eff">HAS NOT BEEN CLAIMED YET!</font></i></td></tr>'
        target_data.append(target_info)
        
    # Sort table and return to view based on scores
    ordered_tokens = sorted(user_information, key=lambda x: (user_information[x]['score']))
    for token in reversed(ordered_tokens):
        username = user_information[token]['username']
        score = user_information[token]['score']
        user_scores_data.append(f'<tr><td>{username}</td><td>{score}</td></tr>')
    return render_template('scoreboard.html', title=title, target_data=target_data, user_scores_data=user_scores_data)

@app.route("/registration", methods=['GET', 'POST'])
def registration_page():
    title = conf['ctf_name']
    if request.method == 'POST':
        username = request.form.get('username')
        username = username.lower().title()
        if register_user(username):
            flash(f'Username "{username}" has already been registered, please select a different username.')
        else:
            flash(f'User "{username}" has successfully been registered!')
    return render_template('registration.html', title=title, users=user_information)

@app.route('/rules', methods=['GET'])
def rules_page():
    title = conf['ctf_name']
    return render_template('rules.html', title=title)

if __name__ == '__main__':
    global conf
    conf = read_yaml()   
    safety_checks(conf)
    
    # Background the read targets function forever updating as needed.
    read_targets_th = threading.Thread(target=read_targets, args=(conf['targets_file'], conf['targets_sleep_timer'],))
    read_targets_th.start()
    
    # Background the save scores function
    save_scores_th = threading.Thread(target=save_scores, args=(conf['scores_file'], conf['periodic_saves'],))
    save_scores_th.start()
    
    # Background query token function
    query_for_tokens_th = threading.Thread(target=query_for_tokens, args=(conf['token_timer'],))
    query_for_tokens_th.start()
    
    # Background scoring function
    score_users_th = threading.Thread(target=score_users, args=(conf['score_timer'], conf['points'],))
    score_users_th.start()

    app.secret_key = conf['app_secret']
    app.run(host='0.0.0.0', port=conf['port'])