# Descope Agentic Crew - AI-Powered Calendar & Contact Management

A modern web application that combines CrewAI's multi-agent intelligence with Descope authentication to provide intelligent calendar and contact management. The system uses AI agents to understand natural language requests and perform Google Calendar and Google Contacts operations seamlessly.

## 🚀 Features

- **Multi-Agent AI System**: Powered by CrewAI with specialized agents for calendar and contact management
- **Natural Language Processing**: Understand and execute complex requests in plain English
- **Google Integration**: Seamless integration with Google Calendar and Google Contacts APIs
- **Modern Web Interface**: React frontend with Vite for fast development and smooth UX
- **Secure Authentication**: Descope-powered authentication with session management
- **RESTful API**: Flask backend with comprehensive error handling and validation

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│    │  Flask Backend  │    │  CrewAI Agents  │
│                 │    │                 │    │                 │
│ • User Interface│◄──►│ • API Endpoints │◄──►│ • Calendar Mgr  │
│ • Authentication│    │ • Session Valid │    │ • Contacts Find │
│ • Request Form  │    │ • Crew Orchestr │    │ • Task Planning │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Descope Auth  │    │  Google APIs    │    │  Custom Tools   │
│                 │    │                 │    │                 │
│ • JWT Tokens    │    │ • Calendar API  │    │ • Calendar Tool │
│ • User Sessions │    │ • Contacts API  │    │ • Contacts Tool │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **Python 3.10+**: Core runtime environment
- **CrewAI**: Multi-agent AI orchestration framework
- **Flask**: Web framework for API endpoints
- **Descope**: Authentication and user management
- **Google APIs**: Calendar and Contacts integration

### Frontend
- **React 19**: Modern UI framework
- **Vite**: Fast build tool and dev server
- **Descope React SDK**: Authentication components
- **Axios**: HTTP client for API communication

## 📋 Prerequisites

- Python 3.10 or higher (but less than 3.14)
- Node.js 18+ and npm/yarn
- Google Cloud Project with Calendar and Contacts APIs enabled
- Descope project with proper configuration

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd crewai-app
```

### 2. Backend Setup
```bash
# Install Python dependencies using UV
pip install uv
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Environment Configuration
Create a `.env` file in the root directory:

```bash
# Descope Configuration
VITE_DESCOPE_PROJECT_ID=your_descope_project_id
VITE_CLIENT_ID=your_client_id

# Google API Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json
GOOGLE_CALENDAR_ID=primary
```

## 🔧 Configuration

### Agents Configuration (`src/descope_agentic_crew/config/agents.yaml`)

The system uses two specialized AI agents:

1. **Calendar Manager**: Handles calendar event creation and management
2. **Contacts Finder**: Searches and retrieves contact information

### Tasks Configuration (`src/descope_agentic_crew/config/tasks.yaml`)

Defines the specific tasks each agent can perform:

- **create_calendar_task**: Creates calendar events from natural language
- **find_contact_task**: Searches contacts using intelligent query generation

## 🚀 Running the Application

### Development Mode

#### Backend
```bash
# From the root directory
python src/descope_agentic_crew/api.py
```

#### Frontend
```bash
cd frontend
npm run dev
```

### Production Build
```bash
# Build frontend
cd frontend
npm run build

# Run backend (serves built frontend)
python src/descope_agentic_crew/api.py
```

## 📱 API Endpoints

### Health Check
```
GET /api/health
```

### Crew Execution
```
POST /api/crew
Authorization: Bearer <session_token>
Content-Type: application/json

{
  "user_request": "Schedule a meeting with John tomorrow at 2 PM"
}
```

## 🔐 Authentication Flow

1. User authenticates through Descope in the React frontend
2. Frontend receives session token and stores it
3. API requests include the session token in Authorization header
4. Backend validates the token with Descope
5. CrewAI agents execute tasks with user context

## 🤖 AI Agents in Action

### Calendar Manager Agent
- **Role**: Calendar Management Specialist
- **Capabilities**: 
  - Parse natural language date/time expressions
  - Create Google Calendar events
  - Handle relative dates ("tomorrow", "next Tuesday")
  - Manage event attendees and locations

### Contacts Finder Agent
- **Role**: Google Contacts Search Specialist
- **Capabilities**:
  - Intelligent contact search queries
  - Fuzzy matching for partial information
  - Comprehensive contact data retrieval
  - Multi-field search optimization

## 🧪 Testing

```bash
# Run tests
uv run test

# Run with coverage
uv run test --cov
```

## 📁 Project Structure

```
crewai-app/
├── src/
│   └── descope_agentic_crew/
│       ├── config/
│       │   ├── agents.yaml      # Agent definitions
│       │   └── tasks.yaml       # Task definitions
│       ├── tools/
│       │   └── custom_tool.py   # Google API integration tools
│       ├── crew.py              # CrewAI crew configuration
│       └── api.py               # Flask API endpoints
├── frontend/                    # React application
│   ├── src/
│   ├── public/
│   └── package.json
├── tests/                       # Test suite
├── pyproject.toml              # Python project configuration
└── README.md                   # This file
```

## 🔧 Customization

### Adding New Agents
1. Define agent configuration in `config/agents.yaml`
2. Create agent method in `crew.py` with `@agent` decorator
3. Implement required tools and capabilities

### Adding New Tasks
1. Define task configuration in `config/tasks.yaml`
2. Create task method in `crew.py` with `@task` decorator
3. Assign appropriate agents to tasks

### Adding New Tools
1. Create custom tool class in `tools/custom_tool.py`
2. Implement required methods and Google API integration
3. Assign tools to relevant agents

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify Descope project ID and client ID
2. **Google API Errors**: Check service account credentials and API enablement
3. **CrewAI Errors**: Ensure Python version compatibility (3.10-3.13)
4. **Frontend Build Errors**: Clear node_modules and reinstall dependencies

### Debug Mode
```bash
# Enable debug logging
export FLASK_DEBUG=1
python src/descope_agentic_crew/api.py
```

## 📚 Documentation

- [CrewAI Documentation](https://docs.crewai.com)
- [Descope Documentation](https://docs.descope.com)
- [Google Calendar API](https://developers.google.com/calendar)
- [Google Contacts API](https://developers.google.com/people)
