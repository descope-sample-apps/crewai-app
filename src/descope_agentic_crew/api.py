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
    descope_client = DescopeClient(project_id=os.getenv("DESCOPE_PROJECT_ID"))
except Exception as error:
    print("failed to initialize. Error:")
    print(error)
    
    
def validate_session(session_token):
    try:
        jwt_response = descope_client.validate_session(session_token=session_token, audience=os.getenv("CLIENT_ID"))
        return jwt_response
    except Exception as error:
        return None

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Initialize Flask app
app = Flask(__name__)
# Enable CORS for React frontend
CORS(app)


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
    
    try:
        print("🚀 Running crew...")
        main_crew = crew_instance.crew() 
        result = main_crew.kickoff(inputs=inputs)
        print(f"✅ Crew result: {result}")
        
        return jsonify({
            "success": True,
            "user_request": user_request,
            "result": str(result)
        })
        
    except Exception as e:
        print(f"❌ Crew execution failed: {str(e)}")
        return jsonify({
            "success": False,
            "user_request": user_request,
            "error": f"Crew execution failed: {str(e)}"
        }), 500
        

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
     
