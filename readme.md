# King of the Hill Capture The Flag Scoreboard

## About
This is a king of the hill capture the flag server, that allows users to compete to see who can hold onto a host for the longest.

----

# Getting Started

## Running via Python
1. Update `settings.yaml` file
    - Server Settings
        - `port` - This option will be the port that you access the server on. You can adjust this to the port number you would like to host the server on. By default it is set to `8080`. 
        -`app_secret` - This is essentially a simple way to allow the server to post messages back to the user in a simple way. Feel free to adjust this as needed.
            - If you would like to read more about it you can read the documentation from Flask located [here](https://flask.palletsprojects.com/en/2.3.x/patterns/flashing/).
- CTF Settings
    - `ctf_name` - Allows you to set both the title of the page, as well as the header of the page so you can rep your logo/name easily. 
    - `targets_sleep_timer` - This is how often the `targets_file` will be re-read. As your CTF progresses, you may want to add additional hosts to the environment for users to own, this will allow you to expand as the competition continues. 
    - `periodic_saves` - This is how often the `scores_file` will be updated. This is the "save" file of all of the username, scores, and tokens.
    - `token_timer` - This is how often a GET request well be made against each host in your `targets_file`. Adjust this as needed if you want to pull more or less frequently from your endpoints.
    - `score_timer` - This is how often scores will updated, in essence, every `score_timer` seconds, `points` will be added to that users score.
    - `points` - How many points a user will receive for holding a particular host.
- Important Files
    - `scores_file` - This is the "save" file in essence that holds the current scores, and unique tokens -> usernames for your capture the flag event.
    - `targets_file` - This is your targets, or end points. Update this file with an IP or hostname to perform a GET requests against in order to look for a particular user token.
    
2. Create a virtual environment and install the requirements
3. Create your virtual environment: `python3 -m venv venv` 
4. Install the required modules:`pip3 install -r requirements.txt`
5. Run your server `python3 main.py` 
    - You should now be able to access the server `http://127.0.0.1:8080` (be sure to update the port if you changed it in the `settings.yaml` file!)

## Running via Docker
1. Update `settings.yaml` file (see the "Running via Python" section)
2. Build the docker image: `docker build . -t kothserver:1.0`
3. Update the `docker-compose.yml` file as needed.
4. Start the server: `docker-compose up -d`
    - You should now be able to access the server `http://127.0.0.1:8080` (be sure to update the port if you changed it in the `settings.yaml` file!)
