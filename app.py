from flask import Flask, render_template, request, jsonify
import logging
import datetime
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from langchain_openai import OpenAI

llm = OpenAI()

# app will run at: http://127.0.0.1:5000/

log = logging.getLogger("app")

logging.basicConfig(filename = "app.log", level = logging.INFO)

app = Flask(__name__)


def log_run(run_status):
    if run_status in ["cancelled", "failed", "expired"]:
        log.error(str(datetime.datetime.now()) + " Run " + run_status + "\n")
        
def build_new_trip_prompt(form_data):
  examples = [
   {  
      "trip_details":
"""
This trip is to Yosemite National Park between 2024-05-23 and 2024-05-25. 
This person will be traveling solo, with kids and would like to stay in campsites. 
They want to hiking, swimming. Create a daily itinerary for this trip using this information.
""",
      "itinerary":
"""
Day 1: May 23, 2024 (Thursday)
Morning: Arrive at Yosemite National Park
Afternoon: Set up campsite at North Pines Campground
Evening: Explore the campground and have a family campfire dinner

Day 2: May 24, 2024 (Friday)
Morning: Guided tour of Yosemite Valley (includes stops at El Capitan, Bridalveil Fall, Half Dome)
Afternoon: Picnic lunch in the Valley
Evening: Relax at the campsite, storytelling around the campfire

Day 3: May 25, 2024 (Saturday)
Morning: Hike to Mirror Lake (easy hike, great for kids)
Afternoon: Swimming at Mirror Lake
Evening: Dinner at the campsite, stargazing
"""
   },
   {  
      "trip_details": "your second example prompt",
      "itinerary": "your second example response"
   },
   {  
      "trip_details": "your third example prompt",
      "itinerary": "your third example response"
   },
  ]

  example_prompt = PromptTemplate.from_template(
    template =
"""
{trip_details}\nItinerary: {itinerary}
"""
  )
  
  # log.info(example_prompt.format(**examples[0]))
  
  few_shot_prompt = FewShotPromptTemplate(
    examples = examples,
    example_prompt = example_prompt,
    suffix = "{input}",
    input_variables = ["input"],
  )

  return few_shot_prompt.format(input = "This trip is to " + form_data["location"] + " between " + form_data["trip_start"] + " and " +  form_data["trip_end"] + ". This person will be traveling " + form_data["traveling_with"] + " and would like to stay in " + form_data["lodging"] + ". They want to " + form_data["adventure"] + ". Create an daily itinerary for this trip using this information.")


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
  
  prompt = build_new_trip_prompt(cleaned_form_data)
  
  response = llm.invoke(prompt)
  log.info(response)

  return render_template("create-trip.html")


    
# Run the flask server
if __name__ == "__main__":
    app.run()
