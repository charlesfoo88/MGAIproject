import React, { useState } from 'react';
import '../styles/main.css';

/**
 * PreferenceInput Component
 * 
 * User input form for match selection and team/player preference.
 * Triggers the MGAI pipeline execution when user submits.
 * 
 * @param {Function} onGenerate - Callback function that receives user preference text
 * @param {Boolean} isLoading - Flag indicating if pipeline is currently running
 * @param {String} matchTitle - Title of the match to display
 * @param {String} matchVenue - Venue of the match to display
 */
function PreferenceInput({ onGenerate, isLoading, matchTitle, matchVenue }) {
  const [userPreference, setUserPreference] = useState('');

  const handleGenerate = () => {
    if (userPreference.trim()) {
      onGenerate(userPreference);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isLoading && userPreference.trim()) {
      handleGenerate();
    }
  };

  return (
    <div className="card">
      {/* Hero Section */}
      <div className="hero">
        <h1>{matchTitle || 'Sports Highlight Generator'}</h1>
        <p className="subtitle">{matchVenue || 'Select your preference below'}</p>
      </div>

      {/* User Input Controls */}
      <div className="controls">
        <div className="field">
          <label htmlFor="preference-input">
            Tell us your team or player preference:
          </label>
          <input
            id="preference-input"
            type="text"
            placeholder="e.g. I am an Arsenal fan and I love watching Saka play!"
            value={userPreference}
            onChange={(e) => setUserPreference(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid #ccc',
              fontSize: '14px',
            }}
          />
        </div>

        <button
          onClick={handleGenerate}
          disabled={isLoading || !userPreference.trim()}
          style={{
            opacity: isLoading || !userPreference.trim() ? 0.6 : 1,
            cursor: isLoading || !userPreference.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          {isLoading ? 'Generating...' : 'Generate Highlights'}
        </button>

        {isLoading && (
          <div className="status" style={{ color: '#2563eb' }}>
            ⚙️ Running AI pipeline... This may take 15-20 seconds.
          </div>
        )}
      </div>
    </div>
  );
}

export default PreferenceInput;
