from flask import Flask, render_template, request, jsonify
import logging
import datetime
from langchain_core.prompts import PromptTemplate

# app will run at: http://127.0.0.1:5000/

log = logging.getLogger("app")

logging.basicConfig(filename = "app.log", level = logging.INFO)

app = Flask(__name__)


def log_run(run_status):
    if run_status in ["cancelled", "failed", "expired"]:
        log.error(str(datetime.datetime.now()) + " Run " + run_status + "\n")
        
def build_new_trip_prompt(form_data):
  prompt_template = PromptTemplate.from_template("This trip is to {location} between {trip_start} and {trip_end}. This person will be traveling {traveling_with} and would like to stay in {lodging}. They want to {adventure}. Create a daily itinerary for this trip using this information.")
  
  return prompt_template.format(
    location = form_data["location"],
    trip_start = form_data["trip_start"],
    trip_end = form_data["trip_end"],
    traveling_with = form_data["traveling_with"],
    lodging = form_data["lodging"],
    adventure = form_data["adventure"]
    )


# Render the HTML template - we're going to see a UI!!!
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")
  
@app.route("/plan_trip", methods=["GET"])
def plan_trip():
  return render_template("plan-trip.html")

@app.route("/create_trip", methods=["POST"])
def create_trip():
  traveling_with_list = ", ".join(request.form.getlist("traveling-with"))
  lodging_list = ", ".join(request.form.getlist("lodging"))
  adventure_list = ", ".join(request.form.getlist("adventure"))
  
  cleaned_form_data = {
    "location": request.form["location-search"],
    "trip_start": request.form["trip-start"],
    "trip_end": request.form["trip-end"],
    "traveling_with": traveling_with_list,
    "lodging": lodging_list,
    "adventure": adventure_list
    }
  
  # log.info(cleaned_form_data)
  # print(cleaned_form_data)
  prompt = build_new_trip_prompt(cleaned_form_data)
  # log.info(prompt)
  return render_template("create-trip.html")


    
# Run the flask server
if __name__ == "__main__":
    app.run()
