#!/usr/bin/env python
import sys
import warnings
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from crew import DescopeAgenticCrew
from crewai import Crew, Process
import requests
from descope import REFRESH_SESSION_TOKEN_NAME, SESSION_TOKEN_NAME, AuthException, DeliveryMethod, DescopeClient

try:
    descope_client = DescopeClient(project_id=os.getenv("VITE_DESCOPE_PROJECT_ID"))
except Exception as error:
    print("failed to initialize. Error:")
    print(error)
    
    
def validate_session(session_token):
    try:
        jwt_response = descope_client.validate_session(session_token=session_token, audience=os.getenv("CLIENT_ID"))
        print("Successfully validated user session:")
        print(jwt_response)
        return jwt_response
    except Exception as error:
        print("Could not validate user session. Error:")
        print(error)
        return None

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for React frontend
CORS(app)
# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "message": "Backend is running!"})

@app.route('/api/crew', methods=['POST'])
def run_crew():
    """
    Run the crew with user choice between research/outreach and calendar management.
    """
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    session_token = auth_header[len('Bearer '):]
    print("session token: " + session_token)
    jwt_response = validate_session(session_token)
    if not jwt_response:
        return jsonify({"error": "Invalid session token"}), 401

    user_id = jwt_response.get("userId")
    if not user_id:
        return jsonify({"error": "User ID not found in token"}), 401

    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    user_request = data.get('user_request')
    inputs = {'user_request': user_request}
    
    crew_instance = DescopeAgenticCrew(user_id=user_id, session_token=session_token)
    
    print(f"Processing request: {user_request}")
    
    # Run both tasks and capture individual results
    calendar_result = None
    contact_result = None
    
    try:
        # Run calendar task
        print("📅 Running calendar task...")
        calendar_task = crew_instance.create_calendar_task()
        calendar_crew = Crew(
            agents=[crew_instance.calendar_manager()],
            tasks=[calendar_task],
            process=Process.sequential,
            verbose=True
        )
        calendar_result = calendar_crew.kickoff(inputs=inputs)
        print(f"📅 Calendar result: {calendar_result}")
    except Exception as e:
        print(f"❌ Calendar task failed: {str(e)}")
        calendar_result = f"Calendar task failed: {str(e)}"
    
    try:
        # Run contact task
        print("👥 Running contact task...")
        contact_task = crew_instance.find_contact_task()
        contact_crew = Crew(
            agents=[crew_instance.contacts_finder()],
            tasks=[contact_task],
            process=Process.sequential,
            verbose=True
        )
        contact_result = contact_crew.kickoff(inputs=inputs)
        print(f"👥 Contact result: {contact_result}")
    except Exception as e:
        print(f"❌ Contact task failed: {str(e)}")
        contact_result = f"Contact task failed: {str(e)}"
    
    # Combine results
    combined_result = ""
    
    if calendar_result:
        combined_result += f"📅 CALENDAR RESULT:\n{calendar_result}\n\n"
    
    if contact_result:
        combined_result += f"👥 CONTACT RESULT:\n{contact_result}\n\n"
    
    if not calendar_result and not contact_result:
        combined_result = "No results from either task."
    
    return jsonify({
        "success": True,
        "user_request": user_request,
        "calendar_result": str(calendar_result) if calendar_result else None,
        "contact_result": str(contact_result) if contact_result else None,
        "combined_result": combined_result
    })
        

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
     
