import logging
import yaml
import csv
import json
import threading
import requests
import re
from os.path import exists
from time import sleep
from flask import Flask, render_template, redirect, url_for, request

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
    user_file = conf['users_file']
    targets_file = conf['targets_file']
    scores_file = conf['scores_file']
    
    if not exists(targets_file):
        logger.error(f'Unable to read the targets file, please make sure the file exists: {targets_file}')
        exit(1)   
    if not exists(user_file):
        logger.error(f'Unable to read the user file, please ensure the file exists: {user_file}')
        exit(1)
        # Maybe add some test here to ensure the user ID is 10 digits or check to ensure users.csv file is correct formatting?...
    # Scores file
    if not exists(scores_file):
        logger.warning(f'Scores file does not exist, a new scores file will be created: {scores_file}')
        create_scores(conf['users_file'], conf['scores_file'])
    
    elif exists(scores_file):
        logger.warning(f'Scores file exists, starting server with previous scores: {scores_file}')
        read_scores(conf['scores_file'])
    
    logger.info('Successfully found required files!')  
    
# Creates a new scores file
def create_scores(users_file, score_file):
    global user_information
    try:
        with open(users_file, mode='r') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                username = row['username']
                token = row['token']
                logger.debug(f'Found user {username} with the unique token {token}!')
                user_information[token] = {'username': username, 'total_boxes': 0, 'hosts': [], 'score': 0}
        logger.info('Loaded all users.')
        csv_file.close()
    except Exception as e:
        logger.error(f'Failed to load users: {e}')
    
    try:
        logger.info(f'Saving scores file: {score_file}')
        with open(score_file, mode='w') as f:
            json.dump(user_information, f, indent=4)
        f.close()
    except Exception as e:
        logger.error(f'Failed to save scores: {e}')

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
            sleep(tgt_sleep)
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
            sleep(periodic_saves)
        except Exception as e:
            logger.error(f'Failed to save scores: {e} - retrying again in {periodic_saves}')
            sleep(periodic_saves)    

def query_for_tokens(token_timer):
    global targets
    while True:
        logger.info(f'Grabbing tokens from targets.')
        for target in targets.keys():
            try:
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
        logger.info(f'Successfully grabbed tokens, will update in {token_timer} seconds.')
        logger.info(targets)
        sleep(token_timer)

def score_users(score_timer, points):
    while True:
        try:
            for token in targets.values():
                user_information[token]['score'] += points  
                user = user_information[token]['username']
                logger.info(f'User {user} scored {points} points!')
                sleep(score_timer)
        except Exception as e:
            logger.debug(f'No boxes has been claimed yet: {e}')
            sleep(score_timer)


# Website Routing Magic
@app.route("/", methods=['GET'])
def index():
    return render_template('scoreboard.html', scoreboard=scoreboard, targets=targets)



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