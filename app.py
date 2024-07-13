from flask import Flask, render_template, request, send_file
import logging
import requests
import json
import os
import io
from langchain_openai import ChatOpenAI
from langchain.agents import create_json_chat_agent, AgentExecutor, tool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import StructuredTool
from langchain import hub
from fuzzywuzzy import fuzz, process
from langchain_openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# app will run at: http://127.0.0.1:5000/

# Initialize logging
logging.basicConfig(filename="app.log", level=logging.INFO)
log = logging.getLogger("app")

# Initialize the Flask application
app = Flask(__name__)

# Initialize the OpenAI language model
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5, max_tokens=4000)

def log_run(run_status):
    """Logs the status of a run if it is cancelled, failed, or expired."""
    if run_status in ["cancelled", "failed", "expired"]:
        log.error(f"{datetime.datetime.now()} Run {run_status}\n")

# Define the route for the home page
@app.route("/", methods=["GET"])
def index():
    """Renders the main page."""
    return render_template("index.html")

# Define the route for the trip planning page
@app.route("/plan_trip", methods=["GET"])
def plan_trip():
    """Renders the trip planning page."""
    parks = get_parks()
    return render_template("plan-trip.html", parks=parks)

def get_parks():
    """Fetches the entire list of national parks from the NPS API."""
    # url = "https://developer.nps.gov/api/v1/parks"
    # todo: try https://developer.nps.gov/api/v1/parks?limit=10 - do they have a random option?
    # adding a limit of 10 brought it down to 27 seconds but is still a long time. And it gave me the entire list???
    url = "https://developer.nps.gov/api/v1/parks?limit=10"
    params = {
        # "api_key": NPS_API_KEY,
        # todo: does this work? If so, need to declare a global variable for NPS_API_KEY
        "api_key": os.environ.get("NPS_API_KEY"),
        # "limit": int(PARK_LIMIT), 
        "limit": 10, # Is 75 in Vincent's code - slow 47 seconds - tried 5 but still received full list and slow - 🤦‍♀️  # Adjust this number based on the API's limit
        "start": 0
    }
    parks = []
    while True:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            parks.extend([{"name": park["fullName"], "code": park["parkCode"]} for park in data["data"]])
            if len(data["data"]) < params["limit"]:
                break
            params["start"] += params["limit"]
        else:
            break
    return parks

# Define the route for viewing the generated trip itinerary
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


@app.route("/download_pdf", methods=["POST"])
def download_pdf():
    """Handles the PDF download of the generated trip itinerary."""
    output = request.json

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph(f"<b>Trip Name:</b> {output['trip_name']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Location:</b> {output['location']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Dates:</b> {output['trip_start']} - {output['trip_end']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Typical Weather:</b> {output['typical_weather']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Traveling With:</b> {output['traveling_with']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Lodging:</b> {output['lodging']}", styles['Normal']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Activities:</b> {output['adventure']}", styles['Normal']))
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("<b>Itinerary:</b>", styles['Normal']))
    elements.append(Spacer(1, 12))
    for day in output['itinerary']:
        elements.append(Paragraph(f"<b>Day {day['day']}:</b> {day['date']}", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>Morning:</b> {day['morning']}", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>Afternoon:</b> {day['afternoon']}", styles['Normal']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>Evening:</b> {day['evening']}", styles['Normal']))
        elements.append(Spacer(1, 24))

    elements.append(Paragraph(f"<b>Important Things to Know:</b> {output['important_things_to_know']}", styles['Normal']))

    doc.build(elements)

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="itinerary.pdf", mimetype='application/pdf')

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

def create_nps_tool():
    """
    Creates a custom tool for retrieving data from the National Park Service (NPS) API. 
    """
    base_url = "https://developer.nps.gov/api/v1"
    # Load your API key from an environment variable
    api_key = os.environ.get("NPS_API_KEY")

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

    def search_parks_by_name(park_name):
        """
        Searches for parks by name.
        """
        return fetch_data("parks", {"q": park_name}).get("data", [])

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

    def find_related_data_for_park(park):
        """
        Finds related data for a park from various NPS API endpoints.
        """
        park_code = park["parkCode"]
        endpoints = [
            "activities/parks" # Add more endpoints as needed. Be mindful of model input token limits these endpoints provide significant amounts of information that could exceed the context window. See https://www.nps.gov/subjects/developer/api-documentation.htm. 
        ]
        related_data = {endpoint: fetch_data(endpoint, {"parkCode": park_code}) for endpoint in endpoints}
        return related_data
    
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