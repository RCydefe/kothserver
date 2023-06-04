from flask import Flask, render_template, redirect, url_for, request
import json
app = Flask(__name__)

# Website Routing Magic
@app.route("/registration", methods=['GET', 'POST'])
def index():
    title = "NolaCon"
    if request.method == 'POST':
        username = request.form.get('username')
        print(username)
    with open('/Users/morbo/Development Projects/Python/Scoreboard2/scores.json', mode='r') as f:
        dict = json.load(f)
    return render_template('registration.html', title=title, parent_list=dict)


if __name__ == '__main__':
    # Starts the webserver
    app.run(ssl_context="adhoc", host='127.0.0.1', port=8080)