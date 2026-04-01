"""
Add a missing player to the knowledge base manually.
Useful for adding historical/former players who appear in match data but aren't in current API squads.

Usage:
    python add_player.py "Kevin De Bruyne" "Manchester City FC" "Midfielder" "Belgium"
    python add_player.py "Sergio Aguero" "Manchester City FC" "Forward" "Argentina" --note "Retired legend, left in 2021"
"""

import json
import sys
import argparse
from pathlib import Path
import wikipediaapi

def get_wikipedia_summary(entity_name: str) -> str:
    """Fetch Wikipedia summary for an entity."""
    try:
        wiki = wikipediaapi.Wikipedia('MGAI-Project/1.0', 'en')
        page = wiki.page(entity_name)
        
        if not page.exists():
            return ""
        
        summary = page.summary
        sentences = summary.split('. ')
        first_three = '. '.join(sentences[:3])
        
        if not first_three.endswith('.'):
            first_three += '.'
        
        return first_three
    
    except Exception as e:
        print(f"⚠ Wikipedia error: {e}")
        return ""

def add_player(name: str, team: str, position: str, nationality: str, note: str = None):
    """Add a player to the knowledge base."""
    
    # Load KB
    kb_path = Path(__file__).parent.parent / "knowledge_base.json"
    print(f"Loading knowledge base...")
    with open(kb_path, 'r', encoding='utf-8') as f:
        kb = json.load(f)
    
    print(f"✓ Current KB has {len(kb['players'])} players\n")
    
    # Generate slug
    slug = name.lower().replace(' ', '_').replace("'", "").replace("-", "_")
    
    # Check if already exists
    if slug in kb['players']:
        print(f"⚠ Player '{name}' already exists in KB (slug: {slug})")
        response = input("Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    
    # Fetch Wikipedia description
    print(f"Fetching '{name}' from Wikipedia...")
    description = get_wikipedia_summary(name)
    
    if not description:
        print(f"⚠ Could not fetch Wikipedia description")
        description = input("Enter description manually (or press Enter to skip): ")
        if not description:
            description = f"{name} is a professional footballer who plays for {team}."
    
    print(f"✓ Got description ({len(description)} chars)\n")
    
    # Generate common aliases
    name_parts = name.split()
    aliases = [name]  # Full name
    
    # Add last name
    if len(name_parts) > 1:
        aliases.append(name_parts[-1])
    
    # Add first name (if not too common)
    common_first_names = ['James', 'John', 'Jack', 'Thomas', 'David', 'Michael', 'Daniel', 'William']
    if len(name_parts) > 1 and name_parts[0] not in common_first_names:
        aliases.append(name_parts[0])
    
    # Add first + last initial (e.g., "Kevin D")
    if len(name_parts) > 1:
        aliases.append(f"{name_parts[0]} {name_parts[-1][0]}")
    
    # Create player entry
    player_entry = {
        "name": name,
        "aliases": list(set(aliases)),  # Remove duplicates
        "position": position,
        "nationality": nationality,
        "team": team,
        "description": description
    }
    
    # Add note if provided
    if note:
        player_entry["_note"] = f"MANUALLY ADDED - {note}"
    else:
        player_entry["_note"] = "MANUALLY ADDED - Not in current API squad data but added for historical match coverage."
    
    # Add to KB
    kb['players'][slug] = player_entry
    
    print("Adding player to knowledge base...")
    print(f"  Slug: {slug}")
    print(f"  Name: {player_entry['name']}")
    print(f"  Team: {player_entry['team']}")
    print(f"  Position: {player_entry['position']}")
    print(f"  Nationality: {player_entry['nationality']}")
    print(f"  Aliases: {', '.join(player_entry['aliases'])}")
    if note:
        print(f"  Note: {note}")
    print()
    
    # Save updated KB
    print("Saving updated knowledge base...")
    with open(kb_path, 'w', encoding='utf-8') as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    
    print("✓ Knowledge base updated!\n")
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Player added: {name}")
    print(f"Total players in KB: {len(kb['players'])}")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(
        description="Add a missing player to the knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python add_player.py "Kevin De Bruyne" "Manchester City FC" "Midfielder" "Belgium"
  python add_player.py "Sergio Aguero" "Manchester City FC" "Forward" "Argentina" --note "Retired legend"
  python add_player.py "Pierre-Emerick Aubameyang" "Arsenal FC" "Forward" "Gabon" --note "Left in 2022"
        """
    )
    
    parser.add_argument("name", help="Player's full name")
    parser.add_argument("team", help="Team name (must match KB team name)")
    parser.add_argument("position", help="Player position (Goalkeeper/Defender/Midfielder/Forward)")
    parser.add_argument("nationality", help="Player nationality")
    parser.add_argument("--note", help="Optional note explaining why player was added", default=None)
    
    args = parser.parse_args()
    
    # Validate position
    valid_positions = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
    if args.position not in valid_positions:
        print(f"⚠ Warning: Position '{args.position}' not standard. Valid: {', '.join(valid_positions)}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    
    add_player(args.name, args.team, args.position, args.nationality, args.note)

if __name__ == "__main__":
    main()
