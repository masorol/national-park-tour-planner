from flask import Flask, render_template, request
import logging
from datetime import datetime
from langchain_openai import ChatOpenAI
from pydantic.v1 import BaseModel, ValidationError, Field
from typing import List

# Initialize the OpenAI language model
llm = ChatOpenAI()

# app will run at: http://127.0.0.1:5000/

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

# Initialize the Flask application
app = Flask(__name__)

# Define the data model
class ItineraryItem(BaseModel):
    day: int = Field(description="The day number of the trip")
    date: str = Field(description="The date of the itinerary item")
    morning: str = Field(description="The morning activity")
    afternoon: str = Field(description="The afternoon activity")
    evening: str = Field(description="The evening activity")

# Define the response model
class TripResponse(BaseModel):
    trip_name: str = Field(description="The name of the trip")
    location: str = Field(description="The location of the trip")
    trip_start: str = Field(description="The start date of the trip")
    trip_end: str = Field(description="The end date of the trip")
    num_days: int = Field(description="The number of days in the trip")
    traveling_with: str = Field(description="The people the traveler is traveling with")
    lodging: str = Field(description="The type of lodging the traveler is staying in")
    adventure: str = Field(description="The activities the traveler wants to do")
    itinerary: List[ItineraryItem] = Field(description="List of itinerary items")

# Define a function to build the new trip prompt 
def build_new_trip_prompt(form_data):
    """Builds a prompt for generating a new trip itinerary based on form data."""
   
    return "This trip is to " + form_data["location"] + " between " + form_data["trip_start"] + " and " +  form_data["trip_end"] + ". This person will be traveling " + form_data["traveling_with_list"] + " and would like to stay in " + form_data["lodging_list"] + ". They want to " + form_data["adventure_list"] + ". Create an daily itinerary for this trip using this information."

# Define the route for the home page
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# Define the route for the plan trip page
@app.route("/plan_trip", methods=["GET"])
def plan_trip():
    return render_template("plan-trip.html")

# Define the route for view trip page with the generated trip itinerary
@app.route("/view_trip", methods=["POST"])
def view_trip():
    traveling_with_list = ", ".join(request.form.getlist("traveling-with"))
    lodging_list = ", ".join(request.form.getlist("lodging"))
    adventure_list = ", ".join(request.form.getlist("adventure"))
    
    cleaned_form_data = {
        "location": request.form["location-search"],
        "trip_start": request.form["trip-start"],
        "trip_end": request.form["trip-end"],
        "traveling_with_list": traveling_with_list,
        "lodging_list": lodging_list,
        "adventure_list": adventure_list,
        "trip_name": request.form["trip-name"]
    }
    
    prompt = build_new_trip_prompt(cleaned_form_data)

    structured_llm = llm.with_structured_output(TripResponse)
    
    # Manually enforce structured output
    response = structured_llm.invoke(prompt)
    
    try:
        log.info(response.json())
        return render_template("view-trip.html", 
                        trip_name=response.trip_name,
                        location=response.location,
                        trip_start=response.trip_start,
                        trip_end=response.trip_end,
                        typical_weather="Typical Weather Information Here",  # Placeholder
                        traveling_with=response.traveling_with,
                        lodging=response.lodging,
                        adventure=response.adventure,
                        itinerary=response.itinerary)
    except (ValidationError, SyntaxError, ValueError) as e:
        log.error(f"Response validation failed: {e}")

# Run the flask server
if __name__ == "__main__":
    app.run()
