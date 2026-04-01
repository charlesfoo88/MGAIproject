"""
Knowledge Base Builder

One-time script to build a rich knowledge_base.json by pulling data from:
- Wikipedia (team/player descriptions)
- football-data.org API (EPL teams, squads, stadiums)

API Key: Add FOOTBALL_DATA_API_KEY to Backend/.env file
Get your free API key at: https://www.football-data.org/client/register

Usage:
    python knowledge_base_builder.py                    # Build all teams
    python knowledge_base_builder.py --batch 5          # Build 5 teams, then pause
    python knowledge_base_builder.py --resume           # Resume from checkpoint

Output: Backend/knowledge_base.json
Checkpoint: Backend/kb_checkpoint.json (temporary, deleted when complete)

What's Included Automatically:
- Teams: name, aliases, description (Wikipedia), venue
- Players: name, aliases, position, nationality, dateOfBirth, description (Wikipedia)
- Stadiums: name, aliases, home_team, description
- Competitions: name, description (Wikipedia)
- Event types: goal, foul, substitution, etc.

What Needs Manual Enrichment (use separate scripts):
- Competition aliases (add_competition_aliases.py)
- Team manager history (add_manager_history.py)
- Additional event types (add_event_types.py)
- Historical/former players (add_player.py)
- Stadium capacity, location (manual or scraping)
"""

import os
import json
import time
import argparse
from pathlib import Path
import requests
import wikipediaapi


# Team nicknames for better entity matching
TEAM_NICKNAMES = {
    'Arsenal FC': ['Gunners', 'The Gunners'],
    'Manchester City FC': ['Man City', 'City', 'Citizens'],
    'Manchester United FC': ['Man United', 'Man Utd', 'Red Devils'],
    'Tottenham Hotspur FC': ['Spurs', 'Tottenham'],
    'Liverpool FC': ['The Reds'],
    'Chelsea FC': ['The Blues'],
    'Newcastle United FC': ['Newcastle', 'Toon'],
    'Aston Villa FC': ['Villa'],
    'West Ham United FC': ['West Ham'],
    'Brighton & Hove Albion FC': ['Brighton'],
}

# Comprehensive stadium aliases based on common usage, fan nicknames, and media references
STADIUM_ALIASES = {
    # Arsenal
    'Emirates Stadium': ['Emirates', 'The Emirates', 'Ashburton Grove'],
    
    # Manchester City
    'Etihad Stadium': ['Etihad', 'The Etihad', 'City of Manchester Stadium', 'COMS', 'Eastlands'],
    
    # Liverpool
    'Anfield': ['Anfield Road', 'The Kop'],
    
    # Manchester United
    'Old Trafford': ['The Theatre of Dreams', 'Theatre of Dreams', 'Old Trafford Stadium'],
    
    # Chelsea
    'Stamford Bridge': ['The Bridge', 'Stamford Bridge Stadium'],
    
    # Tottenham
    'Tottenham Hotspur Stadium': ['Spurs Stadium', 'New White Hart Lane', 'The Tottenham Stadium', 'N17'],
    
    # Newcastle
    "St. James' Park": ['St James Park', "St. James's Park", 'SJP', 'The Gallowgate'],
    
    # Aston Villa
    'Villa Park': ['Villa Park Stadium'],
    
    # Brighton
    'The American Express Community Stadium': ['Amex Stadium', 'The Amex', 'Falmer Stadium'],
    
    # West Ham
    'London Stadium': ['Olympic Stadium', 'The Olympic Stadium', 'Stratford Stadium'],
    
    # Fulham
    'Craven Cottage': ['The Cottage', 'Craven Cottage Stadium'],
    
    # Crystal Palace
    'Selhurst Park': ['Selhurst Park Stadium', 'Selhurst'],
    
    # Wolves
    'Molineux Stadium': ['Molineux', 'The Molineux'],
    
    # Everton
    'Goodison Park': ['Goodison', 'The Grand Old Lady'],
    
    # Leeds United
    'Elland Road': ['Elland Road Stadium', 'ER'],
    
    # Nottingham Forest
    'The City Ground': ['City Ground', 'City Ground Stadium'],
    
    # Burnley
    'Turf Moor': ['Turf Moor Stadium'],
    
    # Sunderland
    'Stadium of Light': ['The Stadium of Light', 'SoL'],
    
    # Bournemouth
    'Vitality Stadium': ['Dean Court', 'The Vitality'],
    
    # Brentford
    'Griffin Park': ['Griffin Park Stadium'],
}


def save_checkpoint(checkpoint_path: str, kb: dict, teams_processed: int, total_teams: int):
    """
    Save progress checkpoint.
    
    Args:
        checkpoint_path: Path to checkpoint file
        kb: Current knowledge base state
        teams_processed: Number of teams processed so far
        total_teams: Total number of teams to process
    """
    checkpoint = {
        "kb": kb,
        "teams_processed": teams_processed,
        "total_teams": total_teams
    }
    
    with open(checkpoint_path, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Checkpoint saved: {teams_processed}/{total_teams} teams processed")


def load_checkpoint(checkpoint_path: str) -> tuple:
    """
    Load progress checkpoint.
    
    Args:
        checkpoint_path: Path to checkpoint file
        
    Returns:
        Tuple of (kb, teams_processed, total_teams) or (None, 0, 0) if no checkpoint
    """
    if not Path(checkpoint_path).exists():
        return None, 0, 0
    
    try:
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
        
        kb = checkpoint.get('kb', {})
        teams_processed = checkpoint.get('teams_processed', 0)
        total_teams = checkpoint.get('total_teams', 0)
        
        print(f"📂 Checkpoint found: {teams_processed}/{total_teams} teams already processed")
        return kb, teams_processed, total_teams
    
    except Exception as e:
        print(f"⚠ Could not load checkpoint: {e}")
        return None, 0, 0


def get_wikipedia_summary(entity_name: str) -> str:
    """
    Fetch Wikipedia summary for an entity.
    
    Args:
        entity_name: Name of the entity (team, player, stadium, etc.)
        
    Returns:
        First 3 sentences of Wikipedia summary, or empty string if not found
    """
    try:
        wiki = wikipediaapi.Wikipedia('MGAI-Project/1.0', 'en')
        page = wiki.page(entity_name)
        
        if not page.exists():
            return ""
        
        # Get summary and extract first 3 sentences
        summary = page.summary
        sentences = summary.split('. ')
        first_three = '. '.join(sentences[:3])
        
        # Add period if not already there
        if not first_three.endswith('.'):
            first_three += '.'
        
        return first_three
    
    except Exception as e:
        print(f"  ⚠ Wikipedia error for '{entity_name}': {e}")
        return ""


def get_epl_teams(api_key: str) -> list:
    """
    Fetch all EPL teams from football-data.org API.
    
    Args:
        api_key: football-data.org API key
        
    Returns:
        List of team dicts with: id, name, shortName, tla, venue
    """
    if not api_key:
        print("⚠ No API key — skipping football-data.org teams fetch")
        return []
    
    try:
        url = "https://api.football-data.org/v4/competitions/PL/teams"
        headers = {'X-Auth-Token': api_key}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        teams = data.get('teams', [])
        
        print(f"✓ Fetched {len(teams)} EPL teams from football-data.org")
        return teams
    
    except requests.exceptions.RequestException as e:
        print(f"⚠ API error fetching teams: {e}")
        return []
    except Exception as e:
        print(f"⚠ Unexpected error fetching teams: {e}")
        return []


def get_team_squad(team_id: int, api_key: str) -> list:
    """
    Fetch team squad from football-data.org API.
    
    Args:
        team_id: Team ID from football-data.org
        api_key: football-data.org API key
        
    Returns:
        List of player dicts with: name, position, nationality
    """
    if not api_key:
        return []
    
    try:
        url = f"https://api.football-data.org/v4/teams/{team_id}"
        headers = {'X-Auth-Token': api_key}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        squad = data.get('squad', [])
        
        return squad
    
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ API error fetching squad for team {team_id}: {e}")
        return []
    except Exception as e:
        print(f"  ⚠ Unexpected error fetching squad: {e}")
        return []


def build_team_entry(team: dict) -> dict:
    """
    Build knowledge base entry for a team.
    
    Args:
        team: Team dict from football-data.org
        
    Returns:
        Structured team entry with Wikipedia description
    """
    team_name = team.get('name', '')
    short_name = team.get('shortName', '')
    tla = team.get('tla', '')
    venue = team.get('venue', '')
    
    # Fetch Wikipedia summary
    print(f"  → Fetching Wikipedia for {team_name}...")
    description = get_wikipedia_summary(team_name)
    
    if not description:
        description = f"{team_name} is a professional football club in the English Premier League."
    
    # Build aliases
    aliases = []
    if short_name and short_name != team_name:
        aliases.append(short_name)
    if tla and tla not in aliases:
        aliases.append(tla)
    # Add version without "FC", "AFC" suffix
    clean_name = team_name.replace(' FC', '').replace(' AFC', '').strip()
    if clean_name != team_name and clean_name not in aliases:
        aliases.append(clean_name)
    # Add short_name without FC
    clean_short = short_name.replace(' FC', '').replace(' AFC', '').strip()
    if clean_short and clean_short not in aliases:
        aliases.append(clean_short)
    # Add team-specific nicknames
    if team_name in TEAM_NICKNAMES:
        for nickname in TEAM_NICKNAMES[team_name]:
            if nickname not in aliases:
                aliases.append(nickname)
    
    return {
        "name": team_name,
        "aliases": aliases,
        "type": "club",
        "venue": venue,
        "description": description
    }


def build_player_entry(player: dict, team_name: str) -> dict:
    """
    Build knowledge base entry for a player.
    
    Args:
        player: Player dict from football-data.org squad
        team_name: Name of the team the player belongs to
        
    Returns:
        Structured player entry with Wikipedia description
    """
    player_name = player.get('name', '')
    position = player.get('position', 'Unknown')
    nationality = player.get('nationality', 'Unknown')
    date_of_birth = player.get('dateOfBirth', None)
    
    # Fetch Wikipedia summary
    description = get_wikipedia_summary(player_name)
    
    if not description:
        description = f"{player_name} is a professional footballer playing for {team_name}."
    
    # Build aliases (last name and first name)
    aliases = []
    name_parts = player_name.split()
    if len(name_parts) > 1:
        last_name = name_parts[-1]
        aliases.append(last_name)
        # Also add first name if it's unique enough (length > 3)
        first_name = name_parts[0]
        if len(first_name) > 3:
            aliases.append(first_name)
    
    player_entry = {
        "name": player_name,
        "aliases": aliases,
        "team": team_name,
        "position": position,
        "nationality": nationality,
        "description": description
    }
    
    # Add dateOfBirth if available (enables age-based context in commentary)
    if date_of_birth:
        player_entry["dateOfBirth"] = date_of_birth
    
    return player_entry


def build_competition_entry(name: str) -> dict:
    """
    Build knowledge base entry for a competition.
    
    Args:
        name: Competition name (e.g., "Premier League")
        
    Returns:
        Structured competition entry with Wikipedia description
    """
    print(f"  → Fetching Wikipedia for {name}...")
    description = get_wikipedia_summary(name)
    
    if not description:
        description = f"{name} is a professional football competition."
    
    return {
        "name": name,
        "description": description
    }


def to_slug(text: str) -> str:
    """
    Convert text to slug format (lowercase, underscores).
    
    Args:
        text: Text to convert
        
    Returns:
        Slug string (e.g., "Manchester City" -> "manchester_city")
    """
    return text.lower().replace(' ', '_').replace('-', '_')


def build_knowledge_base(api_key: str, output_path: str, batch_size: int = None, resume: bool = False):
    """
    Main orchestrator to build the complete knowledge base.
    
    Args:
        api_key: football-data.org API key (optional)
        output_path: Path to save knowledge_base.json
        batch_size: Number of teams to process before pausing (None = all teams)
        resume: Whether to resume from checkpoint
    """
    print("=" * 70)
    print("KNOWLEDGE BASE BUILDER")
    print("=" * 70)
    print()
    
    checkpoint_path = Path(output_path).parent / "kb_checkpoint.json"
    
    # Try to resume from checkpoint if requested
    kb, teams_processed, total_teams = None, 0, 0
    if resume:
        kb, teams_processed, total_teams = load_checkpoint(str(checkpoint_path))
        if kb is None:
            print("⚠ No checkpoint found, starting from scratch")
        else:
            print(f"✓ Resuming from checkpoint: {teams_processed}/{total_teams} teams done")
            print()
    
    # Initialize structure if not resuming
    if kb is None:
        kb = {
            "teams": {},
            "players": {},
            "stadiums": {},
            "competitions": {},
            "matches": {},
            "event_types": {}
        }
        
        # Load existing event_types if knowledge_base.json exists
        if Path(output_path).exists():
            print("Loading existing knowledge base to preserve event_types...")
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    existing_kb = json.load(f)
                    kb['event_types'] = existing_kb.get('event_types', {})
                    print(f"✓ Preserved {len(kb['event_types'])} event types")
            except Exception as e:
                print(f"⚠ Could not load existing KB: {e}")
        
        print()
    
    # Fetch EPL teams
    print("[Step 1] Fetching EPL teams...")
    teams = get_epl_teams(api_key)
    print()
    
    if not teams:
        print("⚠ No teams fetched — will create minimal KB structure")
        print("  Add FOOTBALL_DATA_API_KEY to .env file to fetch full data")
        return
    
    # Calculate which teams to process
    start_index = teams_processed
    if batch_size:
        end_index = min(start_index + batch_size, len(teams))
        print(f"[Batch Mode] Processing teams {start_index + 1} to {end_index} of {len(teams)}")
    else:
        end_index = len(teams)
        print(f"[Full Build] Processing all {len(teams)} teams")
    
    print()
    
    # Build team entries
    print(f"[Step 2] Building team entries...")
    for i in range(start_index, end_index):
        team = teams[i]
        team_name = team.get('name', '')
        team_slug = to_slug(team_name)
        
        print(f"[{i+1}/{len(teams)}] {team_name}")
        
        # Build team entry
        team_entry = build_team_entry(team)
        kb['teams'][team_slug] = team_entry
        
        # Add stadium entry if venue is available
        venue = team.get('venue', '')
        if venue:
            venue_slug = to_slug(venue)
            if venue_slug not in kb['stadiums']:
                # Add aliases for common stadium names
                stadium_aliases = STADIUM_ALIASES.get(venue, [])
                kb['stadiums'][venue_slug] = {
                    "name": venue,
                    "aliases": stadium_aliases,
                    "home_team": team_name,
                    "description": f"{venue} is the home stadium of {team_name}."
                }
        
        # Fetch squad for this team
        team_id = team.get('id')
        if team_id and api_key:
            print(f"  → Fetching squad for {team_name}...")
            squad = get_team_squad(team_id, api_key)
            
            print(f"  ✓ Found {len(squad)} players")
            
            # Build player entries for ALL players
            sample_size = len(squad)
            print(f"  → Fetching Wikipedia for {sample_size} players...")
            
            for j, player in enumerate(squad[:sample_size], 1):
                player_name = player.get('name', '')
                player_slug = to_slug(player_name)
                
                print(f"    [{j}/{sample_size}] {player_name}")
                
                player_entry = build_player_entry(player, team_name)
                kb['players'][player_slug] = player_entry
            
            # Rate limit: 1 second delay between teams
            if i < len(teams) - 1:
                print(f"  ⏳ Rate limiting (1 second delay)...")
                time.sleep(1)
        
        print()
        
        # Save checkpoint after each team
        teams_processed = i + 1
        save_checkpoint(str(checkpoint_path), kb, teams_processed, len(teams))
        print()
    
    # Check if we've finished all teams or just a batch
    if teams_processed < len(teams):
        print("=" * 70)
        print(f"⏸ PAUSED: Processed {teams_processed}/{len(teams)} teams")
        print("=" * 70)
        print(f"Remaining: {len(teams) - teams_processed} teams")
        print()
        print("To continue building:")
        print("  python knowledge_base_builder.py --resume")
        print()
        print(f"Or build next batch:")
        print(f"  python knowledge_base_builder.py --resume --batch {batch_size or 5}")
        print("=" * 70)
        return
    
    # All teams processed - finalize KB
    print("=" * 70)
    print("FINALIZING KNOWLEDGE BASE")
    print("=" * 70)
    print()
    
    # Add Wembley Stadium (neutral venue for cup finals)
    print("[Step 2.5] Adding neutral venues...")
    kb['stadiums']['wembley_stadium'] = {
        "name": "Wembley Stadium",
        "aliases": ["Wembley", "The National Stadium"],
        "city": "London",
        "type": "national stadium",
        "description": "Wembley Stadium is the national football stadium of England, located in Wembley, London. It hosts major cup finals including the FA Cup Final and EFL Cup Final, as well as England national team matches."
    }
    print("  ✓ Added Wembley Stadium")
    print()
    
    # Build competition entries
    print("[Step 3] Building competition entries...")
    competitions = [
        "Premier League",
        "FA Cup",
        "EFL Cup",
        "UEFA Champions League"
    ]
    
    for comp in competitions:
        comp_slug = to_slug(comp)
        print(f"  → {comp}")
        kb['competitions'][comp_slug] = build_competition_entry(comp)
    
    print()
    
    # Save to file
    print(f"[Step 4] Saving knowledge base to {output_path}...")
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(exist_ok=True)
    
    with open(output_path_obj, 'w', encoding='utf-8') as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    
    print("✓ Knowledge base saved successfully!")
    print()
    
    # Delete checkpoint file
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print("✓ Checkpoint file deleted (build complete)")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Teams: {len(kb['teams'])}")
    print(f"Players: {len(kb['players'])}")
    print(f"Stadiums: {len(kb['stadiums'])}")
    print(f"Competitions: {len(kb['competitions'])}")
    print(f"Event Types: {len(kb['event_types'])}")
    print()
    print(f"Output: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Build EPL knowledge base from Wikipedia and football-data.org API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python knowledge_base_builder.py                    # Build all teams (default)
  python knowledge_base_builder.py --batch 5          # Build 5 teams, then pause
  python knowledge_base_builder.py --resume           # Resume from last checkpoint
  python knowledge_base_builder.py --resume --batch 5 # Resume and process 5 more teams
        """
    )
    parser.add_argument('--batch', type=int, default=None,
                        help='Number of teams to process before pausing (default: all teams)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint')
    
    args = parser.parse_args()
    
    # Load API key from .env
    from dotenv import load_dotenv
    load_dotenv()
    
    API_KEY = os.getenv('FOOTBALL_DATA_API_KEY', '')
    
    if not API_KEY:
        print("⚠ Warning: FOOTBALL_DATA_API_KEY not set in .env file")
        print("Only Wikipedia data will be pulled")
        print("Get your free API key at: https://www.football-data.org/client/register")
        print()
    
    # Set output path
    output_path = Path(__file__).parent.parent / "knowledge_base.json"
    
    # Build knowledge base
    build_knowledge_base(API_KEY, str(output_path), batch_size=args.batch, resume=args.resume)
