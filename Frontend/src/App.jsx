import React, { useState } from 'react';
import PreferenceInput from './components/PreferenceInput';
import HighlightReel from './components/HighlightReel';
import './styles/main.css';

/**
 * App - Main Application Component
 * 
 * Manages the state and orchestrates the MGAI highlight generation workflow.
 * Handles API communication with the backend FastAPI server.
 */
function App() {
  // Match configuration — update these when switching to a new match
  const MATCH_NAME = 'arsenal_vs_city_efl_2026'
  const MATCH_TITLE = 'EFL Cup Final 2026 — Arsenal vs Manchester City'
  const MATCH_VENUE = 'Wembley Stadium'

  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Handle highlight generation request
   * Calls the backend API to run the pipeline
   */
  const handleGenerate = async (userPreference) => {
    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch('http://localhost:8000/api/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          match_name: MATCH_NAME,
          user_preference: userPreference,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Pipeline execution error:', err);
      setError(err.message || 'Failed to generate highlights. Please ensure the backend server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="page">
      {/* User Input Form - Always Visible */}
      <PreferenceInput 
        onGenerate={handleGenerate} 
        isLoading={isLoading}
        matchTitle={MATCH_TITLE}
        matchVenue={MATCH_VENUE}
      />

      {/* Loading Indicator */}
      {isLoading && (
        <div className="loading">
          ⚙️ Running AI pipeline... this may take 30-60 seconds
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-box">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results Display */}
      {results && (
        <>
          {/* Stats Bar */}
          <div className="stats-bar">
            <span>
              <strong>Hallucinations Detected:</strong>{' '}
              {results.hallucination_flagged ? '⚠️ Yes' : '✅ No'}
            </span>
            <span>
              <strong>Retries:</strong> {results.retry_count || 0}
            </span>
            <span>
              <strong>Reel A Clips:</strong> {results.reel_a_captions?.length || 0}
            </span>
            <span>
              <strong>Reel B Clips:</strong> {results.reel_b_captions?.length || 0}
            </span>
            <span>
              <strong>Preference Alignment:</strong>{' '}
              <span style={{ color: results.reel_a_alignment_score >= 0.35 ? '#22c55e' : results.reel_a_alignment_score >= 0.20 ? '#f97316' : '#ef4444' }}>
                {results.reel_a_alignment_score ? (results.reel_a_alignment_score * 100).toFixed(0) + '%' : 'N/A'}
              </span>
            </span>
          </div>

          {/* Match Recap Card */}
          {results.match_recap && (
            <div className="card" style={{ borderLeft: '4px solid #2563eb', marginBottom: '20px' }}>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '14px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#2563eb' }}>Match Recap</h3>
              <p style={{ margin: 0, color: '#444', lineHeight: '1.6' }}>{results.match_recap}</p>
            </div>
          )}

          {/* Two-Column Reels Display */}
          <div className="reels-container">
            {/* Reel A - Personalized */}
            <HighlightReel
              title="Reel A — Personalized"
              captions={results.reel_a_captions || []}
              events={results.reel_a_events || []}
              reelType="reel_a"
              matchName={MATCH_NAME}
              videoReady={false}
            />

            {/* Reel B - Neutral */}
            <HighlightReel
              title="Reel B — Neutral"
              captions={results.reel_b_captions || []}
              events={results.reel_b_events || []}
              reelType="reel_b"
              matchName={MATCH_NAME}
              videoReady={false}
            />
          </div>
        </>
      )}
    </div>
  );
}

export default App;
