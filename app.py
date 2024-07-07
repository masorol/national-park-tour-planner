from flask import Flask, render_template, request, jsonify
import logging
import datetime

# app will run at: http://127.0.0.1:5000/

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

app = Flask(__name__)
        
def log_run(run_status):
    """Logs the status of a run if it is cancelled, failed, or expired."""
    if run_status in ["cancelled", "failed", "expired"]:
        log.error(f"{datetime.datetime.now()} Run {run_status}\n")

# Render the HTML template - we're going to see a UI!!!
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")
  
@app.route("/plan_trip", methods=["GET"])
def plan_trip():
  return render_template("plan-trip.html")

@app.route("/view_trip", methods=["POST"])
def view_trip():
  return render_template("view-trip.html")



    
# Run the flask server
if __name__ == "__main__":
    app.run()
