from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, List
import requests
import json
import os
from google.oauth2 import credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_outbound_token(app_id, user_id, access_token):
    """Fetch Google token from Descope Connections vault using the MCP access token."""
    project_id = os.getenv("DESCOPE_PROJECT_ID")

    url = "https://api.descope.com/v1/mgmt/outbound/app/user/token/latest"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {project_id}:{access_token}",
    }
    payload = {
        "appId": app_id,
        "userId": user_id,
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch token: {response.status_code} {response.text}")

    data = response.json()
    return data["token"].get("accessToken")

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
    base_url: str = "https://www.googleapis.com/calendar/v3"

    def __init__(self, user_id=None, access_token=None):
        super().__init__()
        self.user_id = user_id
        self.access_token = access_token

    def _run(self, event_title: Optional[str] = None,
             start_time: Optional[str] = None, end_time: Optional[str] = None,
             description: Optional[str] = None, event_id: Optional[str] = None,
             invitees: Optional[str] = None) -> str:

        google_token = get_outbound_token("google-calendar", self.user_id, self.access_token)

        if not google_token:
            return "Error: No valid access token available for Google Calendar API"

        return self._create_event(google_token, event_title, start_time, end_time, description, invitees)

    def _create_event(self, google_token, title, start_time, end_time, description, invitees=None):
        if not title or not start_time:
            return "Error: title and start_time required"

        try:
            auth = credentials.Credentials(token=google_token)
            
            # Build the Google Calendar service
            service = build("calendar", "v3", credentials=auth)
            
            # Create the event object
            event = {
                'summary': title,
                'description': description or '',
                'start': {'dateTime': start_time, 'timeZone': 'America/Los_Angeles'},
                'end': {'dateTime': end_time or start_time, 'timeZone': 'America/Los_Angeles'}
            }
            
            # Add attendees if provided
            if invitees:
                attendee_emails = [email.strip() for email in invitees.split(',') if email.strip()]
                if attendee_emails:
                    event['attendees'] = [{'email': email} for email in attendee_emails]
            
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

    def __init__(self, user_id=None, access_token=None):
        super().__init__()
        self.user_id = user_id
        self.access_token = access_token

    def _run(self, query: Optional[str] = None,
             max_results: Optional[int] = 10) -> str:

        google_token = get_outbound_token("google-contacts", self.user_id, self.access_token)

        if not google_token:
            return "Error: No valid access token available for Google Contacts API"

        return self._search_contacts(google_token, query, max_results)

    def _search_contacts(self, google_token: str, query: str = None, max_results: int = 10) -> str:
        try:
            auth = credentials.Credentials(token=google_token)

            # Build the Google People service
            service = build("people", "v1", credentials=auth)

            # List the user's contacts and filter client-side. This is more
            # reliable than people.searchContacts, which requires an index
            # warm-up call and typically returns empty on first use.
            people = []
            page_token = None
            while True:
                response = service.people().connections().list(
                    resourceName="people/me",
                    pageSize=1000,
                    personFields="names,emailAddresses,phoneNumbers,organizations,addresses",
                    pageToken=page_token,
                ).execute()
                people.extend(response.get("connections", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            contacts_found = []
            for person in people:
                if self._contact_matches_query(person, query):
                    contacts_found.append(self._format_contact_info(person))
                    if len(contacts_found) >= max_results:
                        break

            if contacts_found:
                return f"Found {len(contacts_found)} contacts:\n\n" + "\n\n".join(contacts_found)
            else:
                return f"No contacts found for query: '{query}'."

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

