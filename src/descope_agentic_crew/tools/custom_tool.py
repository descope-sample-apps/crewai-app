from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, List
import requests
import json
import os
from google.oauth2 import credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_outbound_token(app_id, user_id, session_token):
    """Fetch Google Calendar access token from Descope outbound token API."""
    project_id = os.getenv("VITE_DESCOPE_PROJECT_ID")
    management_key = os.getenv("DESCOPE_MANAGEMENT_KEY")
    
    url = "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {project_id}:{session_token}",
    }

    payload = {
        "appId": app_id,
        "userId": user_id,
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch token: {response.status_code} {response.text}")
    
    data = response.json()
    token_data = data["token"]
    access_token = token_data.get("accessToken")
    return access_token

class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    argument: str = Field(..., description="Description of the argument.")

class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = (
        "Clear description for what this tool is useful for, your agent will need this information to use it."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "this is an example of a tool output, ignore it and move along."  


class CalendarInput(BaseModel):
    """Input schema for Google Calendar operations."""
    event_title: Optional[str] = Field(None, description="Event title")
    start_time: Optional[str] = Field(None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")
    description: Optional[str] = Field(None, description="Event description")
    event_id: Optional[str] = Field(None, description="Event ID for update/delete")
    invitees: Optional[str] = Field(None, description="Comma-separated list of email addresses to invite to the event")

class CalendarCreateTool(BaseTool):
    name: str = "Create Calendar Event"
    description: str = "Create a new event in Google Calendar"
    args_schema: Type[BaseModel] = CalendarInput
    user_id: str = None
    access_token: str = None
    session_token: str = None
    base_url: str = "https://www.googleapis.com/calendar/v3"

    def __init__(self, user_id=None, session_token=None):
        super().__init__()
        self.user_id = user_id
        self.session_token = session_token
        print("user_id: " + user_id)
        print("session_token: " + session_token)
    
    def _run(self, event_title: Optional[str] = None, 
             start_time: Optional[str] = None, end_time: Optional[str] = None,
             description: Optional[str] = None, event_id: Optional[str] = None, 
             invitees: Optional[str] = None) -> str:
        
        self.access_token = get_outbound_token("google-calendar", self.user_id, self.session_token)


        if not self.access_token:
            return "Error: No valid access token available for Google Calendar API"

        return self._create_event(event_title, start_time, end_time, description, invitees)

    def _create_event(self, title, start_time, end_time, description, invitees=None):
        """Create a calendar event using Google Calendar API."""
        if not title or not start_time:
            return "Error: title and start_time required"
        
        try:
            # Create OAuth2 credentials using access token
            auth = credentials.Credentials(token=self.access_token)
            
            # Build the Google Calendar service
            service = build("calendar", "v3", credentials=auth)
            
            # Create the event object
            event = {
                'summary': title,
                'description': description or '',
                'start': {'dateTime': start_time, 'timeZone': 'UTC'},
                'end': {'dateTime': end_time or start_time, 'timeZone': 'UTC'}
            }
            
            # Add attendees if provided
            if invitees:
                attendee_emails = [email.strip() for email in invitees.split(',') if email.strip()]
                if attendee_emails:
                    event['attendees'] = [{'email': email} for email in attendee_emails]
                    print(f"Adding attendees: {attendee_emails}")
            
            print(f"Creating event: {json.dumps(event, indent=2)}")
            
            # Call the Google Calendar API using the official client library
            # Set sendUpdates to 'all' to send email invitations to attendees
            created_event = service.events().insert(
                calendarId='primary', 
                body=event,
                sendUpdates='all'  # Send email invitations to attendees
            ).execute()
            
            # Build response message
            response = f"Event created successfully: {created_event.get('id')} - {created_event.get('summary')}"
            
            if invitees and attendee_emails:
                response += f"\nInvitations sent to: {', '.join(attendee_emails)}"
            
            return response
            
        except HttpError as error:
            return f"Google Calendar API Error: {error}"
        except Exception as e:
            return f"Exception creating event: {str(e)}"


class ContactsInput(BaseModel):
    """Input schema for Google Contacts operations."""
    query: Optional[str] = Field(None, description="Search query to find contacts")
    max_results: Optional[int] = Field(10, description="Maximum number of contacts to return")

class GoogleContactsTool(BaseTool):
    name: str = "Google Contacts Search"
    description: str = "Search and retrieve information from Google Contacts"
    args_schema: Type[BaseModel] = ContactsInput
    user_id: str = None
    access_token: str = None
    session_token: str = None

    def __init__(self, user_id=None, session_token=None):
        super().__init__()
        self.user_id = user_id
        self.session_token = session_token
        print("user_id: " + user_id)
        print("session_token: " + session_token)
    
    def _run(self, query: Optional[str] = None, 
             max_results: Optional[int] = 10) -> str:
        
        self.access_token = get_outbound_token("google-contacts", self.user_id, self.session_token)

        if not self.access_token:
            return "Error: No valid access token available for Google Contacts API"

        return self._search_contacts(query, max_results)

    def _search_contacts(self, query: str = None, max_results: int = 10) -> str:
        """Search contacts using Google People API."""
        try:
            # Create OAuth2 credentials using access token
            auth = credentials.Credentials(token=self.access_token)
            
            # Build the Google People service
            service = build("people", "v1", credentials=auth)
            
            # Try multiple search methods
            contacts_found = []
            
            # Method 1: Try directory search (organization contacts)
            try:
                print(f"Trying directory search for: {query}")
                request = service.people().searchDirectoryPeople(
                    query=query or "",
                    readMask="names,emailAddresses,phoneNumbers,organizations,addresses",
                    sources=["DIRECTORY_SOURCE_TYPE_DOMAIN_PROFILE"],
                    pageSize=max_results
                )
                
                response = request.execute()
                
                if response.get('people'):
                    print(f"Found {len(response['people'])} directory contacts")
                    for person in response['people']:
                        contact_info = self._format_contact_info(person)
                        contacts_found.append(f"[Directory] {contact_info}")
                    
            except HttpError as dir_error:
                print(f"Directory search failed: {dir_error}")
            
            # Method 2: Try personal contacts search
            try:
                print(f"Trying personal contacts search for: {query}")
                request = service.people().searchContacts(
                    query=query or "",
                    readMask="names,emailAddresses,phoneNumbers,organizations,addresses",
                    pageSize=max_results
                )
                
                response = request.execute()
                
                if response.get('results'):
                    print(f"Found {len(response['results'])} personal contacts")
                    for result in response['results']:
                        person = result.get('person', {})
                        contact_info = self._format_contact_info(person)
                        contacts_found.append(f"[Personal] {contact_info}")
                        
            except HttpError as personal_error:
                print(f"Personal contacts search failed: {personal_error}")
            
            # Method 3: Try listing all contacts (fallback)
            if not contacts_found:
                try:
                    print("Trying to list all contacts as fallback")
                    request = service.people().connections().list(
                        resourceName='people/me',
                        pageSize=max_results,
                        personFields="names,emailAddresses,phoneNumbers,organizations,addresses"
                    )
                    
                    response = request.execute()
                    
                    if response.get('connections'):
                        print(f"Found {len(response['connections'])} total contacts")
                        # Filter contacts that match the query
                        for person in response['connections']:
                            if self._contact_matches_query(person, query):
                                contact_info = self._format_contact_info(person)
                                contacts_found.append(f"[All Contacts] {contact_info}")
                                
                except HttpError as list_error:
                    print(f"List contacts failed: {list_error}")
            
            if contacts_found:
                return f"Found {len(contacts_found)} contacts:\n\n" + "\n\n".join(contacts_found)
            else:
                return f"No contacts found for query: '{query}'. Searched directory, personal contacts, and all contacts."
            
        except HttpError as error:
            return f"Google People API Error: {error}"
        except Exception as e:
            return f"Exception searching contacts: {str(e)}"

    def _contact_matches_query(self, person: dict, query: str) -> bool:
        """Check if a contact matches the search query."""
        if not query:
            return True
            
        query_lower = query.lower()
        
        # Check names
        if person.get('names'):
            for name in person['names']:
                display_name = name.get('displayName', '').lower()
                given_name = name.get('givenName', '').lower()
                family_name = name.get('familyName', '').lower()
                if query_lower in display_name or query_lower in given_name or query_lower in family_name:
                    return True
        
        # Check emails
        if person.get('emailAddresses'):
            for email in person['emailAddresses']:
                email_value = email.get('value', '').lower()
                if query_lower in email_value:
                    return True
        
        # Check organizations
        if person.get('organizations'):
            for org in person['organizations']:
                org_name = org.get('name', '').lower()
                if query_lower in org_name:
                    return True
        
        return False

    def _format_contact_info(self, person: dict) -> str:
        """Format contact information for display."""
        info_parts = []
        
        # Name
        if person.get('names'):
            name = person['names'][0]
            display_name = name.get('displayName', 'Unknown')
            info_parts.append(f"Name: {display_name}")
        
        # Email addresses
        if person.get('emailAddresses'):
            emails = [email.get('value', '') for email in person['emailAddresses']]
            info_parts.append(f"Emails: {', '.join(emails)}")
        
        # Phone numbers
        if person.get('phoneNumbers'):
            phones = [phone.get('value', '') for phone in person['phoneNumbers']]
            info_parts.append(f"Phones: {', '.join(phones)}")
        
        # Organizations
        if person.get('organizations'):
            orgs = []
            for org in person['organizations']:
                org_name = org.get('name', '')
                org_title = org.get('title', '')
                if org_name and org_title:
                    orgs.append(f"{org_title} at {org_name}")
                elif org_name:
                    orgs.append(org_name)
                elif org_title:
                    orgs.append(org_title)
            if orgs:
                info_parts.append(f"Organizations: {', '.join(orgs)}")
        
        # Addresses
        if person.get('addresses'):
            addresses = [addr.get('formattedValue', '') for addr in person['addresses']]
            info_parts.append(f"Addresses: {', '.join(addresses)}")
        
        return "\n".join(info_parts) if info_parts else "No contact information available"

