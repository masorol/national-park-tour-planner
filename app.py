from flask import Flask, render_template, request
import logging
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
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
    typical_weather: str = Field(description="The typical weather for the trip")
    itinerary: List[ItineraryItem] = Field(description="List of itinerary items")

# Define a function to build the new trip prompt 
def build_new_trip_prompt():
    """Builds a prompt template for generating a new trip itinerary."""
    return PromptTemplate.from_template("This trip is to {location} between {trip_start} and {trip_end}. This person will be traveling {traveling_with_list} and would like to stay in {lodging_list}. They want to {adventure_list}. Create an daily itinerary for this trip using this information. Set the typical_weather value to empty string.")

# Define a function to build the update weather prompt
def build_weather_prompt():
    """Builds a prompt template for adding weather to an existing trip itinerary."""
    return PromptTemplate.from_template("Update the following JSON object to include typical weather conditions for the trip based on the values of trip_start, trip_end, and location. Keep the object exactly as it is, and update only the typical_weather value with a string describing the typical weather for the time period. {input}")

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
    
     # todo: likely take this out. In the lesson clean_form_data() is changed to output = chain.invoke which is basically below (output/response)
    # cleaned_form_data = {
    #     "location": request.form["location-search"],
    #     "trip_start": request.form["trip-start"],
    #     "trip_end": request.form["trip-end"],
    #     "traveling_with_list": traveling_with_list,
    #     "lodging_list": lodging_list,
    #     "adventure_list": adventure_list,
    #     "trip_name": request.form["trip-name"]
    # }

    try:
    
        structured_llm = llm.with_structured_output(TripResponse)

        # todo: when is this chain invoked?
        chain = build_new_trip_prompt() | structured_llm
        
        # Invoke the chain with the cleaned form data
        response = chain.invoke({
            "location": request.form["location-search"],
            "trip_start": request.form["trip-start"],
            "trip_end": request.form["trip-end"],
            "traveling_with_list": traveling_with_list,
            "lodging_list": lodging_list,
            "adventure_list": adventure_list,
            "trip_name": request.form["trip-name"]
        })

        # Build a new chain to add weather to the trip itinerary
        chain2 = build_weather_prompt() | structured_llm

        response = chain2.invoke({"input": response.dict()})
    
        log.info(response.json())
        return render_template("view-trip.html", output=response)
    
    except (ValidationError, SyntaxError, ValueError) as e:
        log.error(f"Response validation failed: {e}")

# Run the flask server
if __name__ == "__main__":
    app.run()
