from flask import Flask, render_template, request, jsonify
import logging
import datetime

# app will run at: http://127.0.0.1:5000/

# set up logging in the assistant.log file
log = logging.getLogger("app")

logging.basicConfig(filename = "app.log", level = logging.INFO)

app = Flask(__name__)


def log_run(run_status):
    if run_status in ["cancelled", "failed", "expired"]:
        log.error(str(datetime.datetime.now()) + " Run " + run_status + "\n")

# Render the HTML template - we're going to see a UI!!!
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


    
# Run the flask server
if __name__ == "__main__":
    app.run()
