# Knowledge Base Documentation

**File:** `knowledge_base.json`  
**Last Updated:** April 1, 2026  
**Version:** 1.2 (Enriched)

## Overview

Comprehensive football (soccer) knowledge base for the English Premier League, containing structured entity information for RAG (Retrieval-Augmented Generation) fact lookup in match highlight video captioning.

## Contents Summary

### 📊 Statistics

| Entity Type | Count | Coverage |
|------------|-------|----------|
| **Teams** | 20 | All current EPL teams |
| **Players** | 647 | 99.7% with DOB |
| **Stadiums** | 21 | EPL + Wembley |
| **Competitions** | 4 | With aliases |
| **Event Types** | 13 | Expanded coverage |
| **Manager Records** | 39 | Current + 3-year history |

### 🏟️ Entity Types

#### 1. Teams
**Structure:**
```json
{
  "name": "Arsenal FC",
  "aliases": ["Arsenal", "ARS", "Gunners", "The Gunners"],
  "type": "club",
  "venue": "Emirates Stadium",
  "description": "Wikipedia summary...",
  "manager": "Mikel Arteta",
  "manager_history": [
    {
      "name": "Mikel Arteta",
      "appointed": "December 2019",
      "current": true
    }
  ]
}
```

**Coverage:**
- 20 EPL teams
- 20/20 with current manager
- 20/20 with manager history (last 3 seasons)
- 10 teams with nickname aliases (Gunners, Spurs, etc.)

**Notable Teams:**
- Arsenal FC, Manchester City FC, Liverpool FC, Manchester United FC
- Tottenham Hotspur FC, Chelsea FC, Newcastle United FC
- Aston Villa FC, Brighton & Hove Albion FC, West Ham United FC

#### 2. Players
**Structure:**
```json
{
  "name": "Bukayo Saka",
  "aliases": ["Saka", "Bukayo"],
  "position": "Midfielder",
  "nationality": "England",
  "team": "Arsenal FC",
  "dateOfBirth": "2001-09-05",
  "description": "Wikipedia summary..."
}
```

**Coverage:**
- 647 players total
- 645/647 (99.7%) with dateOfBirth
- All with position, nationality, team
- All with Wikipedia descriptions or fallback

**Missing DOB:**
- Luke Rawlings (Wolverhampton - youth player)
- Kevin De Bruyne (Man City - manually added former player)

**Sources:**
- Primary: football-data.org API (current squads)
- Secondary: Manual additions (former/historical players)
- Descriptions: Wikipedia API

#### 3. Stadiums
**Structure:**
```json
{
  "name": "Emirates Stadium",
  "aliases": ["Emirates", "The Emirates", "Ashburton Grove"],
  "home_team": "Arsenal FC",
  "description": "Emirates Stadium is the home stadium of Arsenal FC."
}
```

**Coverage:**
- 21 stadiums total
- 20 EPL team home stadiums
- 1 neutral venue (Wembley Stadium)
- 51 total aliases (avg 2.4 per stadium)

**Notable Aliases:**
- Etihad: ["COMS", "Eastlands", "City of Manchester Stadium"]
- Old Trafford: ["Theatre of Dreams"]
- Tottenham Hotspur Stadium: ["N17", "New White Hart Lane"]
- Anfield: ["The Kop"]
- London Stadium: ["Olympic Stadium"]

#### 4. Competitions
**Structure:**
```json
{
  "name": "Premier League",
  "description": "Wikipedia summary...",
  "aliases": ["Prem", "EPL", "PL", "The Premier League"]
}
```

**Coverage:**
- Premier League (+ 5 aliases)
- FA Cup (+ 3 aliases)
- EFL Cup / Carabao Cup (+ 4 aliases)
- UEFA Champions League (+ 5 aliases)

**Total:** 4 competitions, 17 aliases

#### 5. Event Types
**Structure:**
```json
{
  "label": "Goal",
  "importance": 1.0
}
```

**Coverage:** 13 event types
- **High Importance (0.85-1.0):** goal, red_card, penalty_awarded
- **Medium Importance (0.5-0.7):** stoppage_review (VAR), yellow_card, foul, save, corner_kick, shot_on_target, injury
- **Lower Importance (0.4-0.5):** substitution, offside, shot_off_target

#### 6. Matches
Empty placeholder for future historical match data.

## Data Sources

### Primary Sources
1. **football-data.org API**
   - API Key: Required in `.env` file
   - Coverage: EPL teams, current squads, basic player info
   - Limitations: No historical data, no jersey numbers

2. **Wikipedia API**
   - Coverage: Descriptions for all entities
   - Quality: First 3 sentences of summary
   - Fallback: Generic description if not found

### Manual Enrichments
- Competition aliases
- Stadium aliases (comprehensive)
- Team manager history (2023-2026)
- Additional event types
- Historical/former players (e.g., De Bruyne)

## Building/Updating the Knowledge Base

### Initial Build
```bash
cd Backend/Tools
python knowledge_base_builder.py
```

### Batch Building (Incremental)
```bash
# Build 5 teams at a time
python knowledge_base_builder.py --batch 5

# Resume from checkpoint
python knowledge_base_builder.py --resume
```

### Enrichment Scripts
After building, run these to add enhanced data:

```bash
# Add competition aliases
python add_competition_aliases.py

# Add stadium aliases
python update_stadium_aliases.py

# Add event types
python add_event_types.py

# Add player date of birth
python add_player_dob.py

# Add team manager history
python add_manager_history.py
```

### Adding Individual Players
```bash
# For historical/missing players
python add_player.py "Kevin De Bruyne" "Manchester City FC" "Midfielder" "Belgium" --note "Left in 2026"
```

### Rebuilding a Single Team
```bash
# If squad changes for one team
python rebuild_team.py "Manchester City FC"
```

## Usage in Pipeline

### RAG Tool Integration
```python
from Tools.rag_tool import lookup

# Entity lookup
fact = lookup("Saka")  # Returns player description
fact = lookup("Emirates")  # Returns stadium description
fact = lookup("Prem")  # Returns competition description
```

### Supported Entity References
- **Players:** Full name, last name, first name (if unique), nicknames
- **Teams:** Full name, short name (e.g., "Man City"), nicknames (e.g., "Gunners")
- **Stadiums:** Full name, common names, historical names, neighborhood references
- **Competitions:** Full name, informal names (e.g., "Prem"), acronyms (e.g., "UCL")

## Maintenance

### Regular Updates Needed
- **Player squads:** Update at transfer windows (June, January)
- **Managers:** Update when changes occur
- **Competitions:** Rarely change

### Scripts for Maintenance
- `check_kb_gaps.py` - Analyze missing data
- `check_debruyne.py` - Search for specific players
- `check_mancity.py` - Team-specific diagnostics
- `test_enrichments.py` - Verify all enrichments working

## Version History

### v1.2 (April 1, 2026) - Enriched
- ✅ Added competition aliases (17 total)
- ✅ Expanded event types (5 → 13)
- ✅ Added player dateOfBirth (99.7% coverage)
- ✅ Added team manager history (3 seasons)
- ✅ Enhanced stadium aliases (51 total)
- ✅ Added team nicknames (10 major teams)

### v1.1 (March 2026) - Initial with Basic Aliases
- ✅ Basic team, player, stadium structure
- ✅ Limited stadium aliases (5 stadiums)
- ✅ Basic event types (5 types)

### v1.0 (February 2026) - Initial Build
- ✅ All entities from football-data.org API
- ✅ Wikipedia descriptions
- ✅ Basic structure only

## Notes

### Limitations
- **Jersey numbers:** Not available from API
- **Player height/weight:** Not in current version
- **Historical squads:** Only current squads (except manual additions)
- **Match results:** Empty matches section (future enhancement)

### Data Quality
- **Wikipedia descriptions:** Generally high quality, occasional gaps
- **API data:** Fresh and accurate for current season
- **Manual data:** Manager history based on 2024-2025 season

### Performance
- **File size:** ~2.5MB (manageable for in-memory loading)
- **Load time:** <100ms typical
- **Cache:** RAG tool caches KB in memory after first load

## Related Files

- `Tools/knowledge_base_builder.py` - Main builder script
- `Tools/rag_tool.py` - RAG lookup implementation
- `config.py` - Path configuration (KNOWLEDGE_BASE_PATH)
- `.env` - API key storage (FOOTBALL_DATA_API_KEY)

## Contact/Support

For issues or enhancements, refer to the main project documentation.
