import React from 'react';
import '../styles/main.css';

/**
 * HighlightReel Component
 * 
 * Displays a video player and caption list for either Reel A (personalized)
 * or Reel B (neutral) highlight reels.
 * 
 * @param {String} title - Display title for the reel
 * @param {Array} captions - Array of caption strings
 * @param {Array} events - Array of event objects with event_type, team, clip_start_sec
 * @param {String} reelType - Either "reel_a" or "reel_b"
 * @param {String} matchName - Match identifier for video URL
 * @param {Boolean} videoReady - Whether video file is available to play
 */
function HighlightReel({ title, captions, events, reelType, matchName, videoReady }) {
  
  /**
   * Format seconds to MM:SS timestamp
   */
  const formatTimestamp = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  /**
   * Get badge CSS class based on event type
   */
  const getBadgeClass = (eventType) => {
    const type = eventType?.toLowerCase() || '';
    
    // Goal events
    if (type.includes('goal') || type === 'score_change' || type === 'penalty_goal') {
      return 'badge-goal';
    }
    // Foul events
    if (type.includes('foul') || type === 'foul_or_penalty') {
      return 'badge-foul';
    }
    // Substitution
    if (type === 'substitution') {
      return 'badge-substitution';
    }
    // Penalty awarded
    if (type === 'penalty_awarded') {
      return 'badge-penalty';
    }
    // VAR/Review
    if (type.includes('var') || type.includes('review') || type === 'stoppage_review') {
      return 'badge-var';
    }
    // Default
    return 'badge-default';
  };

  /**
   * Get display label for event type
   */
  const getEventLabel = (eventType) => {
    return eventType?.replace(/_/g, ' ') || 'event';
  };

  // Determine reel title class
  const reelTitleClass = reelType === 'reel_a' 
    ? 'reel-title reel-a' 
    : 'reel-title reel-b';

  // Build video URL
  const videoUrl = `http://localhost:8000/api/videos/${reelType}?match_name=${matchName}`;

  return (
    <div className="output-card">
      {/* Reel Title */}
      <h2 className={reelTitleClass}>{title}</h2>

      {/* Video Player */}
      {videoReady && (
        <div className="video-shell" style={{ marginBottom: '20px' }}>
          <video controls width="100%" src={videoUrl}>
            Your browser does not support the video tag.
          </video>
        </div>
      )}

      {/* Caption List */}
      {captions && captions.length > 0 ? (
        <div>
          <h3 style={{ fontSize: '16px', marginBottom: '10px' }}>Captions:</h3>
          {captions.map((caption, index) => {
            const event = events?.[index] || {};
            const badgeClass = getBadgeClass(event.event_type);
            const eventLabel = getEventLabel(event.event_type);
            const timestamp = event.clip_start_sec 
              ? formatTimestamp(event.clip_start_sec) 
              : '--:--';
            
            return (
              <div key={index} className="caption-item">
                {/* Event Badge */}
                <span className={`event-badge ${badgeClass}`}>
                  {eventLabel}
                </span>
                
                {/* Team and Timestamp */}
                <span style={{ 
                  marginLeft: '8px', 
                  fontSize: '13px', 
                  color: '#666',
                  fontWeight: '600'
                }}>
                  {event.team && `${event.team} • `}
                  {timestamp}
                </span>
                
                {/* Chapter Title */}
                {event.chapter_title && (
                  <p style={{ margin: '4px 0', fontWeight: 'bold', fontSize: '14px', color: reelType === 'reel_a' ? '#22c55e' : '#3b82f6' }}>
                    {event.chapter_title}
                  </p>
                )}
                
                {/* Caption Text */}
                <p className="caption-text" style={{ marginTop: '6px', marginBottom: 0 }}>
                  {caption}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <p style={{ color: '#999', fontStyle: 'italic', textAlign: 'center', padding: '20px' }}>
          Generate highlights to see captions
        </p>
      )}
    </div>
  );
}

export default HighlightReel;
