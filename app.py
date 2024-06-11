from flask import Flask, render_template, request
import logging
import datetime
from langchain_core.prompts.few_shot import FewShotPromptTemplate
from langchain_core.prompts.prompt import PromptTemplate
from langchain_openai import OpenAI
from langchain_core.output_parsers import JsonOutputParser

# app will run at: http://127.0.0.1:5000/

# set up logging in the assistant.log file
log = logging.getLogger("app")

llm = OpenAI(
   max_tokens = -1 # not recommended!!
)

parser = JsonOutputParser()

logging.basicConfig(filename = "app.log", level = logging.INFO)

app = Flask(__name__)

def build_new_trip_prompt_template():
    examples = [
        {
          "prompt":
"""
This trip is to Yosemite National Park between 2024-05-23 and 2024-05-25. This person will be traveling solo, with kids and would like to stay in campsites. They want to go hiking, swimming. Create a daily itinerary for this trip using this information. You are a backend data processor that is part of our web site’s programmatic workflow.  Output the itinerary as only JSON with no text before or after the JSON.
""",
          "response": """{{"trip_name":"My awesome trip to Yosemite 2024 woohoooo","location":"Yosemite National Park","trip_start":"2024-05-23","trip_end":"2024-05-25","num_days":"3","traveling_with":"solo, with kids","lodging":"campsites","adventure":"hiking, swimming","itinerary":[{{"day":"1","date":"2024-05-23","morning":"Arrive at Yosemite National Park","afternoon":"Set up campsite at North Pines Campground","evening":"Explore the campground and have a family campfire dinner"}},{{"day":"2","date":"2024-05-24","morning":"Guided tour of Yosemite Valley (includes stops at El Capitan, Bridalveil Fall, Half Dome)","afternoon":"Picnic lunch in the Valley","evening":"Relax at the campsite, storytelling around the campfire"}},{{"day":"3","date":"2024-05-25","morning":"Hike to Mirror Lake (easy hike, great for kids)","afternoon":"Swimming at Mirror Lake","evening":"Dinner at the campsite, stargazing"}}]}}"""
        },
                {
          "prompt":
"""
This trip is to Yosemite National Park between 2024-05-23 and 2024-05-25. This person will be traveling solo, with kids and would like to stay in campsites. They want to go hiking, swimming. Create a daily itinerary for this trip using this information. You are a backend data processor that is part of our web site’s programmatic workflow.  Output the itinerary as only JSON with no text before or after the JSON.
""",
          "response": """{{"trip_name":"My awesome trip to Yosemite 2024 woohoooo","location":"Yosemite National Park","trip_start":"2024-05-23","trip_end":"2024-05-25","num_days":"3","traveling_with":"solo, with kids","lodging":"campsites","adventure":"hiking, swimming","itinerary":[{{"day":"1","date":"2024-05-23","morning":"Arrive at Yosemite National Park","afternoon":"Set up campsite at North Pines Campground","evening":"Explore the campground and have a family campfire dinner"}},{{"day":"2","date":"2024-05-24","morning":"Guided tour of Yosemite Valley (includes stops at El Capitan, Bridalveil Fall, Half Dome)","afternoon":"Picnic lunch in the Valley","evening":"Relax at the campsite, storytelling around the campfire"}},{{"day":"3","date":"2024-05-25","morning":"Hike to Mirror Lake (easy hike, great for kids)","afternoon":"Swimming at Mirror Lake","evening":"Dinner at the campsite, stargazing"}}]}}"""
        }
    ]

    example_prompt = PromptTemplate.from_template(
      template =
"""
{prompt}\n{response}
"""
    )

    few_shot_prompt = FewShotPromptTemplate(
      examples = examples,
      example_prompt = example_prompt,
      suffix = "This trip is to {location} between {trip_start} and {trip_end}. This person will be traveling {traveling_with_list} and would like to stay in {lodging_list}. They want to {adventure_list}. Create an daily itinerary for this trip using this information. You are a backend data processor that is part of our site's programmatic workflow. Output the itinerary as only JSON with no text before or after the JSON.",
      input_variables = ["location", "trip_start", "trip_end", "traveling_with_list", "lodging_list", "adventure_list"],
    )
    
    return few_shot_prompt

def log_run(run_status):
    if run_status in ["cancelled", "failed", "expired"]:
        log.error(str(datetime.datetime.now()) + " Run " + run_status + "\n")

# Render the HTML template - we're going to see a UI!!!
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")
  
@app.route("/plan_trip", methods=["GET"])
def plan_trip():
  return render_template("plan-trip.html")

@app.route("/view_trip", methods=["POST"])
def view_trip():
  traveling_with_list = ", ".join(request.form.getlist("traveling-with"))
  lodging_list = ", ".join(request.form.getlist("lodging"))
  adventure_list = ", ".join(request.form.getlist("adventure"))

  prompt = build_new_trip_prompt_template()

  chain = prompt | llm | parser

  output = chain.invoke({
    "location": request.form["location-search"],
    "trip_start": request.form["trip-start"],
    "trip_end": request.form["trip-end"],
    "traveling_with_list": traveling_with_list,
    "lodging_list": lodging_list,
    "adventure_list": adventure_list
  })

  return render_template("view-trip.html", output = output)


    
# Run the flask server
if __name__ == "__main__":
    app.run()
