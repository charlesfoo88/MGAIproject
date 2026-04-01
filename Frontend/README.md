# MGAI Frontend

React web application for AI-powered sports highlight generation with personalized and neutral reel views.

## 🎯 Overview

Modern web interface for the MGAI highlight generation pipeline. Users input their team/player preferences and receive two personalized video reels with AI-generated captions and event metadata.

**Key Features:**
- 🎨 Clean, modern UI with hero section
- 📝 User preference input for personalization
- 🎬 Two-column reel display (Personalized vs Neutral)
- 🏷️ Color-coded event badges (goals, fouls, substitutions, VAR, penalties)
- ⏱️ Timestamp formatting for each highlight
- 📱 Responsive design (mobile-friendly)
- 🔄 Loading states and error handling
- 🎥 Video player integration (when videos ready)

**Match Configurability:**
The frontend is match-agnostic. To switch to a new match, update the three constants at the top of `App.jsx`:
- `MATCH_NAME`: Match identifier (used in API call)
- `MATCH_TITLE`: Display title (e.g., "EFL Cup Final 2026 — Arsenal vs Manchester City")
- `MATCH_VENUE`: Display venue (e.g., "Wembley Stadium")

These constants automatically propagate to all child components, eliminating hardcoded values throughout the application.

## 📋 Prerequisites

- **Node.js**: 18.x or higher
- **npm**: 9.x or higher
- **Backend Server**: Must be running at http://localhost:8000

Verify your Node.js installation:
```bash
node --version
npm --version
```

## 🚀 Quick Start

### 1. Install Dependencies

From the `Frontend` directory:

```bash
npm install
```

This installs:
- **react** (^18.x): UI library
- **react-dom** (^18.x): React DOM renderer
- **vite** (^8.0.1): Build tool and dev server

### 2. Start Development Server

```bash
npm run dev
```

The app will be available at:
- **Local**: http://localhost:5173/ (or next available port)
- **Network**: Use `--host` flag to expose

### 3. Ensure Backend is Running

The frontend requires the backend API to be running:

```bash
# In a separate terminal, from Backend/ directory
cd ../Backend
uvicorn main:app --reload
```

Backend should be accessible at: http://localhost:8000

## 📁 Project Structure

```
Frontend/
├── index.html                      # HTML entry point
├── package.json                    # Dependencies and scripts
├── vite.config.js                  # Vite configuration
├── .gitignore
├── src/
│   ├── main.jsx                    # React entry point (createRoot)
│   ├── App.jsx                     # Main app — state management + API calls
│   ├── components/
│   │   ├── PreferenceInput.jsx     # User preference input + match hero section
│   │   └── HighlightReel.jsx       # Caption display + event badges + video player
│   └── styles/
│       └── main.css                # Global styles — layout, badges, cards, responsive
└── public/                         # Static assets
```

## 🧩 Component Architecture

### App.jsx (Main Component)
**Purpose**: Application state management and API orchestration

**Match Configuration Constants:**
- `MATCH_NAME`: Match identifier for API calls (e.g., 'arsenal_vs_city_efl_2026')
- `MATCH_TITLE`: Display title passed to PreferenceInput
- `MATCH_VENUE`: Display venue passed to PreferenceInput

**State:**
- `isLoading`: Boolean for loading indicator
- `results`: API response data (captions, events, metadata)
- `error`: Error message if API call fails

**Key Functions:**
- `handleGenerate(userPreference)`: Calls backend API
  - POST request to `http://localhost:8000/api/run`
  - Body: `{ match_name: MATCH_NAME, user_preference }`
  - Updates state with response

**Renders:**
- `<PreferenceInput />`: User input form
- Loading indicator (during API call)
- Error message (if API fails)
- Stats bar:
  - Hallucination status (✅ No / ⚠️ Yes)
  - Retry count
  - Reel A clip count
  - Reel B clip count
  - Preference Alignment score (color-coded: green ≥35%, orange ≥20%, red <20%)
- Match Recap card (if `match_recap` exists): 3-4 sentence neutral summary of the full match, displayed between stats bar and reel columns
- Two `<HighlightReel />` components (Reel A and Reel B)

### PreferenceInput.jsx
**Purpose**: User preference input with match information

**Props:**
- `onGenerate`: Function to call when Generate button clicked
- `isLoading`: Boolean to disable input during API call
- `matchTitle`: Match title to display in hero section (with fallback: 'Sports Highlight Generator')
- `matchVenue`: Venue to display in hero section (with fallback: 'Select your preference below')

**Features:**
- Hero section: Dynamic match name and venue from props
- Text input with placeholder example
- Generate button (disabled when loading or empty)
- Enter key support
- Loading state with "Generating..." text

**State:**
- `userPreference`: Text input value

### HighlightReel.jsx
**Purpose**: Display video player and caption list for one reel

**Props:**
- `title`: Reel title (e.g., "Reel A — Personalized")
- `captions`: Array of caption strings
- `events`: Array of event objects
- `reelType`: "reel_a" or "reel_b"
- `matchName`: Match identifier for video URL
- `videoReady`: Boolean to show/hide video player

**Features:**
- Reel title with color-coded border (green for A, blue for B)
- Video player (when `videoReady=true`)
  - Source: `http://localhost:8000/api/videos/{reelType}?match_name={matchName}`
  - Controls: play, pause, seek, volume
- Caption list with event metadata:
  - **Event badge**: Color-coded by type (goal, foul, substitution, etc.)
  - **Team name**: Event team
  - **Timestamp**: Formatted as MM:SS
  - **Caption text**: AI-generated description
- Placeholder when no captions

**Helper Functions:**
- `formatTimestamp(seconds)`: Converts seconds to "MM:SS" format
- `getBadgeClass(eventType)`: Maps event type to CSS class

**Event Badge Color Mapping:**
- 🟢 **badge-goal**: goals, score_change, penalty_goal
- 🟠 **badge-foul**: fouls, foul_or_penalty
- ⚫ **badge-substitution**: substitutions
- 🔴 **badge-penalty**: penalty_awarded
- 🟡 **badge-var**: var_review, stoppage_review
- ⚪ **badge-default**: other events

## 🎨 Styling

### Global Styles (main.css)

**Layout:**
- `.page`: Full page container
- `.reels-container`: Two-column grid (1fr 1fr), responsive
- Mobile: Single column on screens < 768px

**Cards:**
- `.card`: Input form container
- `.output-card`: Reel display container
- Rounded corners, shadows, padding

**Reel Components:**
- `.reel-title`: Bold, uppercase, colored left border
  - `.reel-a`: Green border (#22c55e)
  - `.reel-b`: Blue border (#3b82f6)
- `.caption-item`: Single caption with badge + text
- `.caption-text`: Caption content
- `.event-badge`: Small rounded badge with event type

**Badge Variants:**
```css
.badge-goal          { background: #22c55e; }  /* Green */
.badge-foul          { background: #f97316; }  /* Orange */
.badge-substitution  { background: #6b7280; }  /* Grey */
.badge-penalty       { background: #ef4444; }  /* Red */
.badge-var           { background: #eab308; }  /* Yellow */
.badge-default       { background: #94a3b8; }  /* Light grey */
```

**Responsive Design:**
- Desktop: Two-column reel layout
- Tablet: Maintains two columns
- Mobile (<768px): Single column stack

## 🔌 API Integration

### Endpoint: POST /api/run

**Request:**
```json
{
  "match_name": "arsenal_vs_city_efl_2026",
  "user_preference": "I am an Arsenal fan and I love watching Saka play!"
}
```

**Response:**
```json
{
  "status": "success",
  "reel_a_captions": ["Caption 1", "Caption 2"],
  "reel_b_captions": ["Caption 1", "Caption 2"],
  "reel_a_events": [
    {
      "segment_id": "efl_cup_clip_2052",
      "event_type": "goal",
      "team": "Arsenal",
      "clip_start_sec": 2050.0,
      "clip_end_sec": 2058.0
    }
  ],
  "reel_b_events": [...],
  "hallucination_flagged": false,
  "retry_count": 0,
  "reel_a_alignment_score": 0.452,
  "reel_b_alignment_score": 0.305,
  "match_recap": "Arsenal claimed the 2026 EFL Cup Final at Wembley, defeating Manchester City 3-1..."
}
```

### CORS Note

The backend allows all origins during development:
```python
allow_origins=["*"]
```

For production, specify exact frontend origins in `Backend/main.py`.

## 📜 Available Scripts

### Development

```bash
npm run dev
```
Starts Vite dev server with hot module replacement (HMR).
- URL: http://localhost:5173/
- Auto-reloads on file changes

### Build for Production

```bash
npm run build
```
Creates optimized production build in `dist/` folder.
- Minified JavaScript
- Optimized assets
- TypeScript compilation (if using .ts files)

### Preview Production Build

```bash
npm run preview
```
Previews production build locally before deployment.

## 🧪 Testing Frontend-Backend Integration

### 1. Start Both Servers

**Terminal 1 - Backend:**
```bash
cd Backend
uvicorn main:app --reload
```
Wait for: "INFO: Application startup complete."

**Terminal 2 - Frontend:**
```bash
cd Frontend
npm run dev
```
Wait for: "VITE ready" message

### 2. Open Browser

Navigate to: http://localhost:5173/

### 3. Test User Flow

1. **Enter Preference**:
   - Type: "I am an Arsenal fan and I love watching Saka play!"
   - Click "Generate Highlights"

2. **Wait for Processing** (~20-30 seconds):
   - Loading indicator appears
   - Backend runs 3-agent pipeline

3. **View Results**:
   - Stats bar shows metadata (hallucination status, retries, clip counts, preference alignment)
   - Match Recap card displays neutral match summary (if available)
   - Two columns show Reel A (Personalized) and Reel B (Neutral)
   - Each caption has colored badge, team name, timestamp

4. **Check Browser Console** (F12):
   - Should see API response with `reel_a_events` and `reel_b_events`
   - No CORS errors
   - No JavaScript errors

### 4. Verify Backend Logs

Backend terminal should show:
```
INFO: 127.0.0.1 - "POST /api/run HTTP/1.1" 200 OK
[Stage 1] Running sports_analyst_agent...
[Stage 2] Running fan_agent...
[Stage 3] Running critic_agent...
✅ DEMO PIPELINE COMPLETE
```

## 🐛 Troubleshooting

### CORS Errors

**Error:** "Access to fetch at 'http://localhost:8000/api/run' from origin 'http://localhost:5173' has been blocked by CORS"

**Solution:** Ensure CORS middleware is enabled in `Backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Backend Not Running

**Error:** "Failed to fetch" or "net::ERR_CONNECTION_REFUSED"

**Solution:**
1. Check backend terminal for errors
2. Verify backend is at http://localhost:8000
3. Test: `curl http://localhost:8000/api/status`

### Port Already in Use

**Error:** "Port 5173 is in use, trying another one..."

**Solution:** Vite automatically finds next available port (5174, 5175, etc.). Check terminal output for actual URL.

### Node Modules Missing

**Error:** "Cannot find module 'react'"

**Solution:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### Vite Build Errors

**Error:** TypeScript errors during build

**Solution:**
- Frontend uses React (JSX), not TypeScript
- If using `.ts` files, rename to `.jsx`
- Or update `tsconfig.json` to allow JSX

## � Future Enhancements

- Video player integration once DL team confirms source video path
- Multi-sport support with sport-specific event badge mappings
- Match selection dropdown for multiple matches


## 🤝 Contributing

This is a class project for SUTD MDAI program. For questions or improvements, contact the development team.

## 📝 License

Educational project. See main project README for details.

---

**Status:** ✅ Complete and Functional

**Last Updated:** March 31, 2026
