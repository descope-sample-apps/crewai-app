import { useState } from 'react'
import axios from 'axios'
import './App.css'
import { useAuth } from "react-oidc-context";

function App() {
  // State management
  const [userInput, setUserInput] = useState('')
  const [apiResponse, setApiResponse] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const auth = useAuth();

  const isAuthenticated = auth.isAuthenticated;
  const isLoading = auth.isLoading;
  


  // Handle input changes
  const handleInputChange = (e) => {
    setUserInput(e.target.value)
    // Clear error when user starts typing again
    if (errorMessage) {
      setErrorMessage('')
    }
  }

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault()

    // Input validation
    if (!userInput.trim()) {
      setErrorMessage('Please enter a request')
      return
    }
    setErrorMessage('')
    setApiResponse(null)

    try {
      // Get session token for authentication
      const sessionToken = auth.user?.access_token;
      if (!sessionToken) {
        setErrorMessage('Please log in to use the calendar assistant');
        return;
      }
      // Make API call to Flask backend with auth header
      const response = await axios.post('http://localhost:5001/api/crew', {
        user_request: userInput.trim()
      }, {
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json'
        }
      })


      setApiResponse(response.data)
    } catch (error) {
      console.error('API call failed:', error)

      if (error.response?.data?.error) {
        // Server returned an error message
        setErrorMessage(error.response.data.error)
      } else if (error.code === 'ECONNREFUSED') {
        // Server is not running
        setErrorMessage('Cannot connect to server. Make sure your Flask app is running on port 5001.')
      } else {
        // Generic network error
        setErrorMessage('Failed to connect to the server. Please try again.')
      }
    } 
  }

  
  return (<>
    {!isAuthenticated &&
      (
        <div className="login-container">
          <div className="login-content">
            <h1 className="login-title">CrewAI Descope Sample App</h1>
            <p className="login-subtitle">Calendar & Contacts Assistant</p>
            <button 
              className="login-button" 
              onClick={() => void auth.signinRedirect()}
            >
              Log in
            </button>
          </div>
        </div>
      )
    }

    {
      (isLoading) && <p>Loading...</p>
    }

    {isAuthenticated &&
      (
        <div className="app">
          <header className="app-header">
            <h1>Calendar & Contacts Assistant</h1>
            <p>Ask me to manage your calendar events and find contact information</p>
          </header>

          <main className="app-main">
            {/* Input Section */}
            <section className="input-section">
              <form onSubmit={handleSubmit} className="input-form">
                <div className="input-group">
                  <label htmlFor="user-request" className="input-label">
                    What would you like to do with your calendar or contacts?
                  </label>
                  <textarea
                    id="user-request"
                    className="input-textarea"
                    value={userInput}
                    onChange={handleInputChange}
                    placeholder="Examples:
                    • Create a meeting tomorrow at 2pm with John
                    • Find contact information for Sarah
                    • Schedule a team meeting and find their contact info
                    • Search for someone with email john@company.com"
                    rows={4}
                    disabled={isLoading}
                  />
                </div>

                <button
                  type="submit"
                  className={`submit-button ${isLoading ? 'loading' : ''}`}
                  disabled={isLoading || !userInput.trim()}
                >
                  {isLoading ? 'Processing...' : 'Send Request'}
                </button>
              </form>
            </section>

            {/* Output Section */}
            <section className="output-section">
              <div className="output-container">
                {/* Loading Indicator */}
                {isLoading && (
                  <div className="loading-container">
                    <div className="spinner"></div>
                    <p className="loading-text">Processing your request...</p>
                    <p className="loading-subtext">This may take a few seconds</p>
                  </div>
                )}

                {/* Error Message */}
                {errorMessage && (
                  <div className="error-message">
                    <h3>❌ Error</h3>
                    <p>{errorMessage}</p>
                  </div>
                )}

                {/* Success Response */}
                {apiResponse && (
                  <div className="success-response">
                    <h3>✅ Response</h3>
                    
                    {/* Simple Result Display */}
                    <div className="result-content">
                      <pre className="result-text">
                        {apiResponse.combined_result || apiResponse.result || 'No results available'}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Empty State */}
                {!isLoading && !errorMessage && !apiResponse && (
                  <div className="empty-state">
                    <p>👆 Enter a request above to get started</p>
                    <div className="example-requests">
                      <h4>Try these examples:</h4>
                      <ul>
                        <li>"Create a meeting tomorrow at 2pm with John"</li>
                        <li>"Find contact information for Sarah"</li>
                        <li>"Schedule a team meeting and find their contact info"</li>
                        <li>"Search for someone with email john@company.com"</li>
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </section>
          </main>
        </div>
      )
    }
  </>


  )
}

export default App
