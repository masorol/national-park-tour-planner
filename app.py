from flask import Flask, render_template, request
import logging
from datetime import datetime
import requests
import json
from langchain_openai import ChatOpenAI
from langchain.agents import create_json_chat_agent, AgentExecutor, tool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import StructuredTool
from langchain import hub
from fuzzywuzzy import fuzz, process
import os # for NPS API key

# app will run at: http://127.0.0.1:5000/

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

# Initialize the Flask application
app = Flask(__name__)

# Initialize the OpenAI language model
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5, max_tokens=4000)

# Define the route for the home page
@app.route("/", methods=["GET"])
def index():
    """Renders the main page."""
    return render_template("index.html")

# Define the route for the plan trip page
@app.route("/plan_trip", methods=["GET"])
def plan_trip():
    """Renders the trip planning page."""
    return render_template("plan-trip.html")

# Define the route for view trip page with the generated trip itinerary
@app.route("/view_trip", methods=["POST"])
def view_trip():
    """Handles the form submission to view the generated trip itinerary."""
    # Extract form data
    location = request.form["location-search"]
    trip_start = request.form["trip-start"]
    trip_end = request.form["trip-end"]
    traveling_with_list = ", ".join(request.form.getlist("traveling-with"))
    lodging_list = ", ".join(request.form.getlist("lodging"))
    adventure_list = ", ".join(request.form.getlist("adventure"))

    # Create the input string with the user's unique trip information
    input_data = generate_trip_input(location, trip_start, trip_end, traveling_with_list, lodging_list, adventure_list)

    # Create a tool for the agent to use that utilizes Wikipedia's run function
    wikipedia_tool = create_wikipedia_tool()

    # Define and register a custom tool for retrieving data from the National Park Service API
    nps_tool = create_nps_tool()

    # Pull a tool prompt template from the hub
    prompt = hub.pull("hwchase17/react-chat-json")

    # Create our agent that will utilize tools and return JSON
    agent = create_json_chat_agent(llm=llm, tools=[wikipedia_tool, nps_tool], prompt=prompt)

    # Create a runnable instance of the agent
    agent_executor = AgentExecutor(agent=agent, tools=[wikipedia_tool, nps_tool], verbose=True, handle_parsing_errors="Check your output and make sure it conforms to the expected JSON structure.")

    # Invoke the agent with the input data
    response = agent_executor.invoke({"input": input_data})

    log.info(response["output"])

    # Render the response on the view-trip.html page
    return render_template("view-trip.html", output=response["output"])

# Define a function to generate the input string
def generate_trip_input(location, trip_start, trip_end, traveling_with, lodging, adventure):
    """
    Generates a structured input string for the trip planning agent.
    """
    return f"""
    Create an itinerary for a trip to {location}.
    The trip starts on: {trip_start}
    The trip ends on: {trip_end}
    I will be traveling with {traveling_with}
    I would like to stay in {lodging}
    I would like to do the following activities: {adventure}

    Please generate a complete and detailed trip itinerary with the following JSON data structure:

    {{
      "trip_name": "String - Name of the trip",
      "location": "String - Location of the trip",
      "trip_start": "String - Start date of the trip",
      "trip_end": "String - End date of the trip",
      "typical_weather": "String - Description of typical weather for the trip",
      "traveling_with": "String - Description of travel companions",
      "lodging": "String - Description of lodging arrangements",
      "adventure": "String - Description of planned activities",
      "itinerary": [
        {{
          "day": "Integer - Day number",
          "date": "String - Date of this day",
          "morning": "String - Description of morning activities",
          "afternoon": "String - Description of afternoon activities",
          "evening": "String - Description of evening activities"
        }}
      ],
      "important_things_to_know": "String - Any important things to know about the park being visited."
    }}

    The trip should be appropriate for those listed as traveling, themed around the interests specified, and that last for the entire specified duration of the trip.
    Include realistic and varied activities for each day, considering the location, hours of operation, and typical weather.
    Make sure all fields are filled with appropriate and engaging content.
    Include descriptive information about each day's activities and destination.
    Respond only with a valid parseable JSON object representing the itinerary.
    """

# Define a function to create the Wikipedia tool
def create_wikipedia_tool():
    """
    Creates a built-in langchain tool for querying Wikipedia.
    """
    wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    return StructuredTool.from_function(
        func=wikipedia.run,
        name="Wikipedia",
        description="Useful for Wikipedia searches about national parks."
    )

# Define a function to create the National Park Service tool
def create_nps_tool():
    """
    Creates a custom tool for retrieving data from the National Park Service (NPS) API. 
    """
    base_url = "https://developer.nps.gov/api/v1"

    # Load your API key from an environment variable
    api_key = os.environ.get("NPS_API_KEY")
    # print(api_key)
    # log.info(api_key)

    # Define a function to fetch data from the NPS API
    def fetch_data(endpoint, params):
        """
        Fetches data from the NPS API given an endpoint and parameters.
        """
        url = f"{base_url}/{endpoint}"
        params['api_key'] = api_key
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Failed to fetch data from {endpoint}, status code: {response.status_code}"}

    # Define a function to search for parks by name using the NPS API
    def search_parks_by_name(park_name):
        """
        Searches for parks by name.
        """
        return fetch_data("parks", {"q": park_name}).get("data", [])

    # Define a function to find the best matching park
    def find_best_matching_park(park_name, parks):
        """
        Finds the best matching park using fuzzy search.
        """
        park_names = [park['fullName'] for park in parks]
        best_match_name, _ = process.extractOne(park_name, park_names, scorer=fuzz.partial_ratio)
        for park in parks:
            if park['fullName'] == best_match_name:
                return park
        return None

    # Define a function to find related data for a park
    def find_related_data_for_park(park):
        """
        Finds related data for a park from various NPS API endpoints.
        """
        park_code = park["parkCode"]
        endpoints = [ "activities/parks"
            #, "thingstodo" # Add more endpoints as needed. Be mindful of model input token limits these endpoints provide significant amounts of information that could exceed the context window. See https://www.nps.gov/subjects/developer/api-documentation.htm. 
        ]
        related_data = {endpoint: fetch_data(endpoint, {"parkCode": park_code}) for endpoint in endpoints}
        return related_data
    
    # Define a tool for searching for parks and related data
    @tool
    def search_park_and_related_data(input: str) -> str:
        """
        Searches for a park and finds related data.
        """
        park_name = input.strip()
        parks = search_parks_by_name(park_name)
        if parks:
            best_matching_park = find_best_matching_park(park_name, parks)
            if best_matching_park:
                combined_data = {
                    "park": best_matching_park,
                    "related_data": find_related_data_for_park(best_matching_park)
                }
            else:
                combined_data = {"error": f"Exact park named '{park_name}' not found in search results."}
        else:
            combined_data = {"error": f"Park named '{park_name}' not found."}
        return json.dumps(combined_data, indent=4)

    return search_park_and_related_data

# Run the Flask server
if __name__ == "__main__":
    app.run()