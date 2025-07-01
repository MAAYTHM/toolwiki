#!/usr/bin/env python3
"""
Kali Tool Wiki - Dual-Mode Tool Management System
================================================

A comprehensive tool for managing and documenting installed tools in Kali Linux environments.
Supports both interactive menu mode and CLI mode with extensive search and export capabilities.

Author: Generated for Kali Linux Tool Management
Version: 2.0
License: MIT
"""

import argparse
import json
import os
import sys
import shutil
import re
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import csv

# Third-party imports (install via requirements.txt)
try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("❌ Error: jsonschema not installed. Run: pip install jsonschema")
    sys.exit(1)

try:
    import colorama
    from colorama import Fore, Back, Style, init
    init(autoreset=True)  # Auto-reset colors after each print
    HAS_COLORAMA = True
except ImportError:
    print("⚠️  Warning: colorama not installed. Colors disabled. Install with: pip install colorama")
    HAS_COLORAMA = False

try:
    from rapidfuzz import fuzz, process
    HAS_FUZZY = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz, process
        HAS_FUZZY = True
    except ImportError:
        print("⚠️  Warning: fuzzy search disabled. Install rapidfuzz or fuzzywuzzy for fuzzy search.")
        HAS_FUZZY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    print("⚠️  Warning: pandas not installed. CSV export limited. Install with: pip install pandas")
    HAS_PANDAS = False

# Constants
VERSION = "2.0"
APP_NAME = "Kali Tool Wiki"
CONFIG_DIR = Path("config")
DATA_DIR = Path("data")
BACKUP_DIR = DATA_DIR / "backups"
DEFAULT_DATA_FILE = DATA_DIR / "tools.json"
DEFAULT_CONFIG_FILE = CONFIG_DIR / "settings.json"
SCHEMA_FILE = CONFIG_DIR / "schema.json"
LEGEND = """
Legend:
  ✅  - Tool path is verified and accessible
  ❌  - Tool path is not accessible or not found
  ℹ️  - Information or neutral status
  🔍  - Search operation
  📁  - Category
  📍  - File path
  💬  - Description text
  ⚠️  - Warning
  🔧  - Tool-related operation
  📤  - Export operation
  ⚙️  - Settings
  📋  - List view
  🗑️  - Delete operation
  ✏️  - Update operation
  ➕  - Add operation
"""


# Create directories if they don't exist
for directory in [CONFIG_DIR, DATA_DIR, BACKUP_DIR]:
    directory.mkdir(exist_ok=True)

# =============================================================================
# Color Management System
# =============================================================================

class ColorManager:
    """Manages terminal colors with support for NO_COLOR environment variable."""
    
    def __init__(self, enabled: bool = True):
        """Initialize color manager with color enabled/disabled state."""
        self.enabled = enabled and HAS_COLORAMA and not os.environ.get('NO_COLOR')
        
        # Color mappings
        self.colors = {
            'success': Fore.GREEN if self.enabled else '',
            'error': Fore.RED if self.enabled else '',
            'info': Fore.BLUE if self.enabled else '',
            'warning': Fore.YELLOW if self.enabled else '',
            'highlight': Fore.CYAN if self.enabled else '',
            'bold': Style.BRIGHT if self.enabled else '',
            'reset': Style.RESET_ALL if self.enabled else ''
        }
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.enabled or color not in self.colors:
            return text
        return f"{self.colors[color]}{text}{self.colors['reset']}"
    
    def success(self, text: str) -> str:
        """Apply success color (green)."""
        return self.colorize(text, 'success')
    
    def error(self, text: str) -> str:
        """Apply error color (red)."""
        return self.colorize(text, 'error')
    
    def info(self, text: str) -> str:
        """Apply info color (blue)."""
        return self.colorize(text, 'info')
    
    def warning(self, text: str) -> str:
        """Apply warning color (yellow)."""
        return self.colorize(text, 'warning')
    
    def highlight(self, text: str) -> str:
        """Apply highlight color (cyan)."""
        return self.colorize(text, 'highlight')
    
    def bold(self, text: str) -> str:
        """Apply bold formatting."""
        return self.colorize(text, 'bold')

# =============================================================================
# Data Management and Validation
# =============================================================================

class DataManager:
    """Handles all data operations including JSON file management, validation, and backups."""
    
    def __init__(self, data_file: Path = DEFAULT_DATA_FILE, 
                 config_file: Path = DEFAULT_CONFIG_FILE,
                 color_manager: ColorManager = None):
        """Initialize data manager with file paths and color support."""
        self.data_file = Path(data_file)
        self.config_file = Path(config_file)
        self.color = color_manager or ColorManager()
        self.schema = self._load_schema()
        self.config = self._load_config()
        self.data = self._load_data()
        self.is_new_data = False
        
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema for data validation."""
        try:
            if SCHEMA_FILE.exists():
                with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create default schema if it doesn't exist
                self._create_default_schema()
                return self._load_schema()
        except Exception as e:
            print(self.color.warning(f"⚠️  Warning: Could not load schema: {e}"))
            return {}
    
    def _create_default_schema(self):
        """Create default JSON schema file."""
        schema = {
            "type": "object",
            "required": ["metadata", "categories", "tools"],
            "properties": {
                "metadata": {
                    "type": "object",
                    "required": ["version", "created", "last_modified", "total_tools"],
                    "properties": {
                        "version": {"type": "string"},
                        "created": {"type": "string"},
                        "last_modified": {"type": "string"},
                        "total_tools": {"type": "integer", "minimum": 0}
                    }
                },
                "categories": {"type": "array", "items": {"type": "string"}},
                "tools": {"type": "array", "items": {"type": "object"}}
            }
        }
        
        with open(SCHEMA_FILE, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration settings."""
        default_config = {
            "backup_retention": 5,
            "search_defaults": {"fuzzy": True, "limit": 20},
            "show_legend_on_start": True,
            "colors": {"enabled": True}
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                return default_config
        except Exception as e:
            print(self.color.warning(f"⚠️  Warning: Could not load config: {e}"))
            return default_config
    
    def _load_data(self) -> Dict[str, Any]:
        """Load tool data from JSON file."""
        try:
            if self.data_file.exists():
                if self.data_file.stat().st_size == 0:
                    self.is_new_data = True  # Mark as new data
                    return self._create_default_data()

                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if self.schema:
                        validate(data, self.schema)
                    return data
            else:
                self.is_new_data = True  # Mark as new data
                # Create default data structure
                return self._create_default_data()
        except ValidationError as e:
            print(self.color.error(f"❌ Data validation error: {e.message}"))
            backup_path = self._create_backup()
            print(self.color.info(f"📦 Corrupted data backed up to: {backup_path}"))
            return self._create_default_data()
        except Exception as e:
            print(self.color.error(f"❌ Error loading data: {e}"))
            return self._create_default_data()
    
    def _create_default_data(self) -> Dict[str, Any]:
        """Create default data structure."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "metadata": {
                "version": VERSION,
                "created": now,
                "last_modified": now,
                "total_tools": 0,
                "mode_usage": {"menu": 0, "cli": 0}
            },
            "categories": ["network", "forensics", "web", "system", "custom"],
            "tools": []
        }
    
    def save_data(self) -> bool:
        """Save data to JSON file with backup."""
        try:
            # Create backup before saving
            if self.data_file.exists():
                self._create_backup()
            
            # Update metadata
            self.data["metadata"]["last_modified"] = datetime.now(timezone.utc).isoformat()
            self.data["metadata"]["total_tools"] = len(self.data["tools"])
            
            # Validate before saving
            if self.schema:
                validate(self.data, self.schema)
            
            # Save to file
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(self.color.error(f"❌ Error saving data: {e}"))
            return False
    
    def _create_backup(self) -> str:
        """Create a timestamped backup of the data file."""
        if not self.data_file.exists():
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"tools_backup_{timestamp}.json"
        
        try:
            shutil.copy2(self.data_file, backup_path)
            self._cleanup_old_backups()
            return str(backup_path)
        except Exception as e:
            print(self.color.warning(f"⚠️  Warning: Could not create backup: {e}"))
            return ""
    
    def _cleanup_old_backups(self):
        """Remove old backup files based on retention policy."""
        try:
            backup_files = sorted(BACKUP_DIR.glob("tools_backup_*.json"))
            retention_count = self.config.get("backup_retention", 5)
            
            if len(backup_files) > retention_count:
                for backup_file in backup_files[:-retention_count]:
                    backup_file.unlink()
        except Exception as e:
            print(self.color.warning(f"⚠️  Warning: Could not cleanup backups: {e}"))

# =============================================================================
# Search Engine
# =============================================================================

class SearchEngine:
    """Advanced search engine with fuzzy search, regex, and multi-field filtering."""
    
    def __init__(self, color_manager: ColorManager):
        """Initialize search engine with color support."""
        self.color = color_manager
    
    def search_tools(self, tools: List[Dict], query: str = "", 
                    category: str = "", tags: List[str] = None,
                    search_type: str = "fuzzy", field: str = "all",
                    limit: int = 20) -> List[Dict]:
        """Search tools with various filters and search types."""
        results = tools.copy()
        
        # Filter by category
        if category:
            results = [tool for tool in results 
                      if tool.get('category', '').lower() == category.lower()]
        
        # Filter by tags
        if tags:
            tag_set = set(tag.lower() for tag in tags)
            results = [tool for tool in results 
                      if tag_set.intersection(set(tag.lower() for tag in tool.get('tags', [])))]
        
        # Apply text search
        if query:
            results = self._apply_text_search(results, query, search_type, field)
        
        # Sort by relevance if fuzzy search
        if search_type == "fuzzy" and query and HAS_FUZZY:
            results = self._sort_by_relevance(results, query, field)
        
        return results[:limit]
    
    def _apply_text_search(self, tools: List[Dict], query: str, 
                          search_type: str, field: str) -> List[Dict]:
        """Apply text search based on search type and field."""
        if search_type == "fuzzy" and HAS_FUZZY:
            return self._fuzzy_search(tools, query, field)
        elif search_type == "regex":
            return self._regex_search(tools, query, field)
        elif search_type == "exact":
            return self._exact_search(tools, query, field)
        else:  # partial
            return self._partial_search(tools, query, field)
    
    def _fuzzy_search(self, tools: List[Dict], query: str, field: str) -> List[Dict]:
        """Perform fuzzy search on tools."""
        results = []
        threshold = 60  # Minimum similarity score
        
        for tool in tools:
            if field == "all":
                search_text = f"{tool.get('name', '')} {tool.get('description', '')} {tool.get('path', '')}"
            else:
                search_text = tool.get(field, '')
            
            if search_text:
                similarity = fuzz.partial_ratio(query.lower(), search_text.lower())
                if similarity >= threshold:
                    tool['_search_score'] = similarity
                    results.append(tool)
        
        return results
    
    def _regex_search(self, tools: List[Dict], pattern: str, field: str) -> List[Dict]:
        """Perform regex search on tools."""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            results = []
            
            for tool in tools:
                if field == "all":
                    search_text = f"{tool.get('name', '')} {tool.get('description', '')} {tool.get('path', '')}"
                else:
                    search_text = tool.get(field, '')
                
                if search_text and regex.search(search_text):
                    results.append(tool)
            
            return results
        except re.error as e:
            print(self.color.error(f"❌ Invalid regex pattern: {e}"))
            return []
    
    def _exact_search(self, tools: List[Dict], query: str, field: str) -> List[Dict]:
        """Perform exact search on tools."""
        results = []
        query_lower = query.lower()
        
        for tool in tools:
            if field == "all":
                search_text = f"{tool.get('name', '')} {tool.get('description', '')} {tool.get('path', '')}"
            else:
                search_text = tool.get(field, '')
            
            if search_text and query_lower == search_text.lower():
                results.append(tool)
        
        return results
    
    def _partial_search(self, tools: List[Dict], query: str, field: str) -> List[Dict]:
        """Perform partial (substring) search on tools."""
        results = []
        query_lower = query.lower()
        
        for tool in tools:
            if field == "all":
                search_text = f"{tool.get('name', '')} {tool.get('description', '')} {tool.get('path', '')}"
            else:
                search_text = tool.get(field, '')
            
            if search_text and query_lower in search_text.lower():
                results.append(tool)
        
        return results
    
    def _sort_by_relevance(self, tools: List[Dict], query: str, field: str) -> List[Dict]:
        """Sort tools by search relevance score."""
        return sorted(tools, key=lambda x: x.get('_search_score', 0), reverse=True)

# =============================================================================
# Tool Management
# =============================================================================

class ToolManager:
    """Manages tool operations including CRUD operations and validation."""
    
    def __init__(self, data_manager: DataManager):
        """Initialize tool manager with data manager instance."""
        self.data_manager = data_manager
        self.color = data_manager.color
        self.search_engine = SearchEngine(self.color)
    
    def add_tool(self, name: str, path: str, description: str = "", 
                category: str = "", tags: List[str] = None,
                example_usage: str = "", notes: str = "") -> bool:
        """Add a new tool to the database."""
        try:
            # Validate required fields
            if not name or not path:
                print(self.color.error("❌ Name and path are required"))
                return False
            
            # Check if tool already exists
            if self._tool_exists(name):
                print(self.color.error(f"❌ Tool '{name}' already exists"))
                return False
            
            # Create tool dictionary
            now = datetime.now(timezone.utc).isoformat()
            tool = {
                "id": str(uuid.uuid4()),
                "name": name,
                "path": path,
                "description": description,
                "category": category or "custom",
                "tags": tags or [],
                "example_usage": example_usage,
                "date_added": now,
                "last_modified": now,
                "last_accessed": now,
                "access_count": 0,
                "notes": notes,
                "verified": self._verify_tool_path(path),
                "verification_date": now
            }
            
            # Add to database
            self.data_manager.data["tools"].append(tool)
            
            # Add category if new
            if category and category not in self.data_manager.data["categories"]:
                self.data_manager.data["categories"].append(category)
            
            # Save data
            if self.data_manager.save_data():
                print(self.color.success(f"✅ Tool '{name}' added successfully"))
                return True
            else:
                print(self.color.error("❌ Failed to save tool"))
                return False
                
        except Exception as e:
            print(self.color.error(f"❌ Error adding tool: {e}"))
            return False
    
    def _tool_exists(self, name: str) -> bool:
        """Check if a tool with the given name already exists."""
        return any(tool["name"].lower() == name.lower() 
                  for tool in self.data_manager.data["tools"])
    
    def _verify_tool_path(self, path: str) -> bool:
        """Verify if the tool path exists and is executable."""
        try:
            tool_path = Path(path)
            return tool_path.exists() and os.access(tool_path, os.X_OK)
        except Exception:
            return False
    
    def get_tool_by_name(self, name: str) -> Optional[Dict]:
        """Get tool by name."""
        for tool in self.data_manager.data["tools"]:
            if tool["name"].lower() == name.lower():
                return tool
        return None
    
    def update_tool(self, name: str, **kwargs) -> bool:
        """Update tool with new values."""
        try:
            tool = self.get_tool_by_name(name)
            if not tool:
                print(self.color.error(f"❌ Tool '{name}' not found"))
                return False
            
            # Update fields
            for key, value in kwargs.items():
                if key in tool and value is not None:
                    tool[key] = value
            
            # Update timestamp
            tool["last_modified"] = datetime.now(timezone.utc).isoformat()
            
            # Re-verify if path changed
            if "path" in kwargs:
                tool["verified"] = self._verify_tool_path(kwargs["path"])
                tool["verification_date"] = datetime.now(timezone.utc).isoformat()
            
            # Save data
            if self.data_manager.save_data():
                print(self.color.success(f"✅ Tool '{name}' updated successfully"))
                return True
            else:
                print(self.color.error("❌ Failed to save changes"))
                return False
                
        except Exception as e:
            print(self.color.error(f"❌ Error updating tool: {e}"))
            return False
    
    def delete_tool(self, name: str, confirm: bool = False) -> bool:
        """Delete tool by name."""
        try:
            tool = self.get_tool_by_name(name)
            if not tool:
                print(self.color.error(f"❌ Tool '{name}' not found"))
                return False
            
            if not confirm:
                print(self.color.warning(f"⚠️  Use --confirm flag to delete '{name}'"))
                return False
            
            # Remove from list
            self.data_manager.data["tools"] = [
                t for t in self.data_manager.data["tools"] 
                if t["name"].lower() != name.lower()
            ]
            
            # Save data
            if self.data_manager.save_data():
                print(self.color.success(f"✅ Tool '{name}' deleted successfully"))
                return True
            else:
                print(self.color.error("❌ Failed to save changes"))
                return False
                
        except Exception as e:
            print(self.color.error(f"❌ Error deleting tool: {e}"))
            return False
    
    def list_tools(self, category: str = "", sort_by: str = "name", 
                  reverse: bool = False, limit: int = None) -> List[Dict]:
        """List tools with optional filtering and sorting."""
        tools = self.data_manager.data["tools"].copy()
        
        # Filter by category
        if category:
            tools = [tool for tool in tools 
                    if tool.get("category", "").lower() == category.lower()]
        
        # Sort tools
        if sort_by in ["name", "category", "date_added", "last_modified"]:
            tools.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
        
        # Apply limit
        if limit:
            tools = tools[:limit]
        
        return tools
    
    def get_categories(self) -> List[str]:
        """Get list of available categories."""
        return self.data_manager.data.get("categories", [])
    
    def search_tools(self, **kwargs) -> List[Dict]:
        """Search tools using the search engine."""
        return self.search_engine.search_tools(
            self.data_manager.data["tools"], **kwargs
        )

# =============================================================================
# CLI Interface
# =============================================================================

def setup_cli_parser() -> argparse.ArgumentParser:
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{VERSION} - Personal Tool Documentation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Use --show-legend to display icon meanings\n\n{LEGEND}

Examples:
  %(prog)s add -n "nmap" -p "/usr/bin/nmap" -d "Network scanner"
  %(prog)s search -n "nmap" --fuzzy
  %(prog)s list --category network --sort name
  %(prog)s export -f csv -o tools.csv
        """
    )
    
    # Global options
    parser.add_argument('-V', '--version', action='version', version=f'{APP_NAME} v{VERSION}')
    parser.add_argument('--no-color', action='store_true', help='disable colored output')
    parser.add_argument('--interactive', action='store_true', help='force interactive mode')
    parser.add_argument('--show-legend', action='store_true', help='display icon legend and exit')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='available commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='add new tool')
    add_parser.add_argument('-n', '--name', required=True, help='tool name')
    add_parser.add_argument('-p', '--path', required=True, help='tool executable path')
    add_parser.add_argument('-d', '--description', help='tool description')
    add_parser.add_argument('-c', '--category', help='tool category')
    add_parser.add_argument('-t', '--tags', help='comma-separated tags')
    add_parser.add_argument('-u', '--usage', help='example usage')
    add_parser.add_argument('--notes', help='additional notes')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='search tools')
    search_parser.add_argument('-n', '--name', help='search by name')
    search_parser.add_argument('-d', '--description', help='search in descriptions')
    search_parser.add_argument('-c', '--category', help='filter by category')
    search_parser.add_argument('-t', '--tags', help='search by tags (comma-separated)')
    search_parser.add_argument('-p', '--path', help='search by path')
    search_parser.add_argument('-f', '--fuzzy', action='store_true', help='enable fuzzy search')
    search_parser.add_argument('-r', '--regex', action='store_true', help='use regex search')
    search_parser.add_argument('--limit', type=int, default=20, help='limit results')
    
    # List command
    list_parser = subparsers.add_parser('list', help='list tools')
    list_parser.add_argument('-c', '--category', help='filter by category')
    list_parser.add_argument('-s', '--sort', choices=['name', 'category', 'date_added'], 
                           default='name', help='sort by field')
    list_parser.add_argument('--reverse', action='store_true', help='reverse sort order')
    list_parser.add_argument('--limit', type=int, help='limit results')
    list_parser.add_argument('--count', action='store_true', help='show count only')
    list_parser.add_argument('--categories', action='store_true', help='list categories')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='update existing tool')
    update_parser.add_argument('name', help='tool name to update')
    update_parser.add_argument('-p', '--path', help='new tool path')
    update_parser.add_argument('-d', '--description', help='new description')
    update_parser.add_argument('-c', '--category', help='new category')
    update_parser.add_argument('-t', '--tags', help='new tags (comma-separated)')
    update_parser.add_argument('-u', '--usage', help='new example usage')
    update_parser.add_argument('--notes', help='new notes')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='delete tool')
    delete_parser.add_argument('name', help='tool name to delete')
    delete_parser.add_argument('--confirm', action='store_true', help='confirm deletion')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='export data')
    export_parser.add_argument('-f', '--format', choices=['csv', 'json', 'markdown'], 
                             default='json', help='export format')
    export_parser.add_argument('-o', '--output', required=True, help='output file path')
    export_parser.add_argument('--filter', help='filter expression')
    
    return parser

def handle_cli_command(args, tool_manager: ToolManager) -> bool:
    """Handle CLI commands."""
    try:
        if args.command == 'add':
            tags = [tag.strip() for tag in args.tags.split(',')] if args.tags else []
            return tool_manager.add_tool(
                name=args.name,
                path=args.path,
                description=args.description or "",
                category=args.category or "",
                tags=tags,
                example_usage=args.usage or "",
                notes=args.notes or ""
            )
        
        elif args.command == 'search':
            # Determine search type
            search_type = 'fuzzy' if args.fuzzy else 'regex' if args.regex else 'partial'
            
            # Build search parameters
            search_params = {
                'search_type': search_type,
                'limit': args.limit
            }
            
            if args.name:
                search_params.update({'query': args.name, 'field': 'name'})
            elif args.description:
                search_params.update({'query': args.description, 'field': 'description'})
            elif args.path:
                search_params.update({'query': args.path, 'field': 'path'})
            
            if args.category:
                search_params['category'] = args.category
                
            if args.tags:
                search_params['tags'] = [tag.strip() for tag in args.tags.split(',')]
            
            results = tool_manager.search_tools(**search_params)
            
            if results:
                print(f"🎯 Found {len(results)} matching tools:")
                for i, tool in enumerate(results, 1):
                    verified = "✅" if tool.get('verified') else "❌"
                    print(f"{i}. {tool['name']} {verified}")
                    print(f"   📁 {tool.get('category', 'N/A')} | 📍 {tool['path']}")
                    if tool.get('description'):
                        desc = tool['description'][:60] + "..." if len(tool['description']) > 60 else tool['description']
                        print(f"   💬 {desc}")
                    print()
            else:
                print("ℹ️  No tools found matching your criteria")
            
            return True
        
        elif args.command == 'list':
            if args.categories:
                categories = tool_manager.get_categories()
                print(f"📁 Available categories ({len(categories)}):")
                for category in sorted(categories):
                    count = len([t for t in tool_manager.data_manager.data["tools"] 
                               if t.get('category') == category])
                    print(f"  • {category} ({count} tools)")
                return True
            
            tools = tool_manager.list_tools(
                category=args.category or "",
                sort_by=args.sort,
                reverse=args.reverse,
                limit=args.limit
            )
            
            if args.count:
                print(f"📊 Total tools: {len(tools)}")
                return True
            
            if tools:
                print(f"🔧 Tools ({len(tools)}):")
                for i, tool in enumerate(tools, 1):
                    verified = "✅" if tool.get('verified') else "❌"
                    print(f"{i}. {tool['name']} {verified}")
                    print(f"   📁 {tool.get('category', 'N/A')} | 📍 {tool['path']}")
                    print()
            else:
                print("ℹ️  No tools found")
            
            return True
        
        elif args.command == 'update':
            update_params = {}
            if args.path:
                update_params['path'] = args.path
            if args.description:
                update_params['description'] = args.description
            if args.category:
                update_params['category'] = args.category
            if args.tags:
                update_params['tags'] = [tag.strip() for tag in args.tags.split(',')]
            if args.usage:
                update_params['example_usage'] = args.usage
            if args.notes:
                update_params['notes'] = args.notes
            
            if not update_params:
                print("⚠️  No update parameters provided")
                return False
            
            return tool_manager.update_tool(args.name, **update_params)
        
        elif args.command == 'delete':
            return tool_manager.delete_tool(args.name, confirm=args.confirm)
        
        elif args.command == 'export':
            tools = tool_manager.data_manager.data["tools"]
            
            # Apply filter if provided
            if args.filter:
                # Simple category filter for now
                if args.filter.startswith('category='):
                    category = args.filter.split('=', 1)[1]
                    tools = [t for t in tools if t.get('category') == category]
            
            # Export data
            from pathlib import Path
            output_path = Path(args.output)
            
            if args.format == 'csv':
                return export_csv(tools, output_path, tool_manager.color)
            elif args.format == 'json':
                return export_json(tools, output_path, tool_manager.color)
            elif args.format == 'markdown':
                return export_markdown(tools, output_path, tool_manager.color)
        
        else:
            print(f"❌ Unknown command: {args.command}")
            return False
    
    except Exception as e:
        print(tool_manager.color.error(f"❌ Command failed: {e}"))
        return False

def export_csv(tools: List[Dict], output_file: Path, color: ColorManager) -> bool:
    """Export tools to CSV format."""
    try:
        if HAS_PANDAS:
            df = pd.DataFrame(tools)
            df.to_csv(output_file, index=False)
        else:
            if not tools:
                print(color.warning("⚠️  No tools to export"))
                return False
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=tools[0].keys())
                writer.writeheader()
                writer.writerows(tools)
        
        print(color.success(f"✅ Exported {len(tools)} tools to {output_file}"))
        return True
    except Exception as e:
        print(color.error(f"❌ Export failed: {e}"))
        return False

def export_json(tools: List[Dict], output_file: Path, color: ColorManager) -> bool:
    """Export tools to JSON format."""
    try:
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_tools": len(tools),
            "tools": tools
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(color.success(f"✅ Exported {len(tools)} tools to {output_file}"))
        return True
    except Exception as e:
        print(color.error(f"❌ Export failed: {e}"))
        return False

def export_markdown(tools: List[Dict], output_file: Path, color: ColorManager) -> bool:
    """Export tools to Markdown format."""
    try:
        markdown_content = "# Tool Documentation\n\n"
        markdown_content += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        markdown_content += f"Total tools: {len(tools)}\n\n"
        
        # Group by category
        categories = {}
        for tool in tools:
            category = tool.get('category', 'Uncategorized')
            if category not in categories:
                categories[category] = []
            categories[category].append(tool)
        
        for category, category_tools in categories.items():
            markdown_content += f"## {category.title()}\n\n"
            
            for tool in category_tools:
                markdown_content += f"### {tool['name']}\n\n"
                markdown_content += f"**Path:** `{tool['path']}`\n\n"
                if tool.get('description'):
                    markdown_content += f"**Description:** {tool['description']}\n\n"
                if tool.get('example_usage'):
                    markdown_content += f"**Usage:**\n``````\n\n"
                if tool.get('tags'):
                    tags = ', '.join(tool['tags'])
                    markdown_content += f"**Tags:** {tags}\n\n"
                markdown_content += "---\n\n"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(color.success(f"✅ Exported {len(tools)} tools to {output_file}"))
        return True
    except Exception as e:
        print(color.error(f"❌ Export failed: {e}"))
        return False

# =============================================================================
# Interactive Menu Interface
# =============================================================================

class MenuInterface:
    """Interactive menu-driven interface for tool management."""
    
    def __init__(self, tool_manager: ToolManager):
        """Initialize menu interface with tool manager."""
        self.tool_manager = tool_manager
        self.color = tool_manager.color
        self.running = True
    
    def show_banner(self):
        """Display application banner."""
        banner = f"""
┌─────────────────────────────────────────────────────────────┐
│                    {APP_NAME} v{VERSION}                     │
│              Personal Tool Documentation System             │
└─────────────────────────────────────────────────────────────┘
        """
        print(self.color.highlight(banner))
    
    def show_main_menu(self):
        """Display main menu options."""
        tools_count = len(self.tool_manager.data_manager.data["tools"])
        categories_count = len(self.tool_manager.get_categories())
        
        menu = f"""
🔧 Main Menu:
 [1] Add New Tool        [6] Export Data
 [2] Search Tools        [7] List Categories  
 [3] Update Tool         [8] Verify Tools
 [4] Delete Tool         [9] Settings
 [5] List All Tools      [0] Exit

📊 Statistics: {tools_count} tools | {categories_count} categories
⚡ Quick Actions: [a]dd [s]earch [l]ist [h]elp [q]uit
        """
        print(menu)
    
    def get_user_choice(self, prompt: str = "Enter your choice: ") -> str:
        """Get user input with prompt."""
        try:
            return input(self.color.info(prompt)).strip()
        except KeyboardInterrupt:
            print(self.color.warning("\n⚠️  Operation cancelled"))
            return ""
        except EOFError:
            print(self.color.warning("\n⚠️  Input ended"))
            return "0"  # Exit
    
    def confirm_action(self, message: str) -> bool:
        """Ask user for confirmation."""
        response = self.get_user_choice(f"{message} (y/N): ").lower()
        return response in ['y', 'yes']
    
    def run(self):
        """Main menu loop."""
        self.show_banner()
        
        # Update mode usage
        self.tool_manager.data_manager.data["metadata"]["mode_usage"]["menu"] += 1
        
        while self.running:
            try:
                self.show_main_menu()
                choice = self.get_user_choice().lower()
                
                if choice in ['1', 'a', 'add']:
                    self.add_tool_menu()
                elif choice in ['2', 's', 'search']:
                    self.search_tools_menu()
                elif choice in ['3', 'u', 'update']:
                    self.update_tool_menu()
                elif choice in ['4', 'd', 'delete']:
                    self.delete_tool_menu()
                elif choice in ['5', 'l', 'list']:
                    self.list_tools_menu()
                elif choice in ['6', 'e', 'export']:
                    self.export_menu()
                elif choice in ['7', 'categories']:
                    self.list_categories_menu()
                elif choice in ['8', 'v', 'verify']:
                    self.verify_tools_menu()
                elif choice in ['9', 'settings']:
                    self.settings_menu()
                elif choice in ['h', 'help']:
                    self.show_help()
                elif choice in ['0', 'q', 'quit', 'exit']:
                    self.running = False
                    print(self.color.success("👋 Thank you for using Kali Tool Wiki!"))
                else:
                    print(self.color.warning("⚠️  Invalid choice. Type 'h' for help."))
                    
            except KeyboardInterrupt:
                print(self.color.warning("\n⚠️  Use '0' or 'quit' to exit properly."))
            except Exception as e:
                print(self.color.error(f"❌ An error occurred: {e}"))
    
    def add_tool_menu(self):
        """Interactive tool addition menu."""
        print(self.color.highlight("\n➕ Adding New Tool"))
        print("─" * 30)
        
        name = self.get_user_choice("Tool name (required): ")
        if not name:
            print(self.color.warning("⚠️  Tool name is required"))
            return
        
        path = self.get_user_choice("Tool path (required): ")
        if not path:
            print(self.color.warning("⚠️  Tool path is required"))
            return
        
        description = self.get_user_choice("Description (optional): ")
        
        # Show available categories
        categories = self.tool_manager.get_categories()
        print(f"\nAvailable categories: {', '.join(categories)}")
        category = self.get_user_choice("Category (or create new): ")
        
        tags_input = self.get_user_choice("Tags (comma-separated): ")
        tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
        
        usage = self.get_user_choice("Example usage: ")
        notes = self.get_user_choice("Notes: ")
        
        if self.confirm_action("\nAdd this tool?"):
            self.tool_manager.add_tool(
                name=name, path=path, description=description,
                category=category, tags=tags, example_usage=usage, notes=notes
            )
    
    def search_tools_menu(self):
        """Interactive search menu."""
        print(self.color.highlight("\n🔍 Search Tools"))
        print("─" * 20)
        
        query = self.get_user_choice("Search query: ")
        if not query:
            print(self.color.warning("⚠️  Search query is required"))
            return
        
        results = self.tool_manager.search_tools(query=query, search_type="fuzzy", limit=10)
        
        if results:
            print(f"\n🎯 Found {len(results)} tools:")
            for i, tool in enumerate(results, 1):
                verified = "✅" if tool.get('verified') else "❌"
                print(f"{i}. {tool['name']} {verified}")
                print(f"   📁 {tool.get('category')} | 📍 {tool['path']}")
                if tool.get('description'):
                    desc = tool['description'][:50] + "..." if len(tool['description']) > 50 else tool['description']
                    print(f"   💬 {desc}")
                print()
        else:
            print(self.color.info("ℹ️  No tools found"))
    
    def list_tools_menu(self):
        """List tools menu."""
        print(self.color.highlight("\n📋 List Tools"))
        print("─" * 15)
        
        category = self.get_user_choice("Filter by category (optional): ")
        tools = self.tool_manager.list_tools(category=category)
        
        if tools:
            print(f"\n🔧 Found {len(tools)} tools:")
            for i, tool in enumerate(tools, 1):
                verified = "✅" if tool.get('verified') else "❌"
                print(f"{i}. {tool['name']} {verified}")
                print(f"   📁 {tool.get('category')} | 📍 {tool['path']}")
                print()
        else:
            print(self.color.info("ℹ️  No tools found"))
    
    def list_categories_menu(self):
        """List categories menu."""
        categories = self.tool_manager.get_categories()
        print(f"\n📁 Categories ({len(categories)}):")
        for category in sorted(categories):
            count = len([t for t in self.tool_manager.data_manager.data["tools"] 
                        if t.get('category') == category])
            print(f"  • {category} ({count} tools)")
    
    def update_tool_menu(self):
        """Update tool menu."""
        print(self.color.highlight("\n✏️  Update Tool"))
        print("─" * 15)
        
        name = self.get_user_choice("Tool name to update: ")
        if not name:
            return
        
        tool = self.tool_manager.get_tool_by_name(name)
        if not tool:
            print(self.color.error(f"❌ Tool '{name}' not found"))
            return
        
        print(f"\nCurrent values for '{name}':")
        print(f"Path: {tool['path']}")
        print(f"Description: {tool.get('description', 'N/A')}")
        print(f"Category: {tool.get('category', 'N/A')}")
        
        updates = {}
        new_path = self.get_user_choice("New path (Enter to keep current): ")
        if new_path:
            updates['path'] = new_path
        
        new_desc = self.get_user_choice("New description (Enter to keep current): ")
        if new_desc:
            updates['description'] = new_desc
        
        if updates and self.confirm_action("Save changes?"):
            self.tool_manager.update_tool(name, **updates)
    
    def delete_tool_menu(self):
        """Delete tool menu."""
        print(self.color.highlight("\n🗑️  Delete Tool"))
        print("─" * 15)
        
        name = self.get_user_choice("Tool name to delete: ")
        if not name:
            return
        
        tool = self.tool_manager.get_tool_by_name(name)
        if not tool:
            print(self.color.error(f"❌ Tool '{name}' not found"))
            return
        
        print(f"\nTool to delete: {name}")
        print(f"Path: {tool['path']}")
        
        if self.confirm_action(f"⚠️  Are you sure you want to delete '{name}'?"):
            self.tool_manager.delete_tool(name, confirm=True)
    
    def export_menu(self):
        """Export data menu."""
        print(self.color.highlight("\n📤 Export Data"))
        print("─" * 15)
        
        print("Export formats:")
        print("[1] CSV")
        print("[2] JSON") 
        print("[3] Markdown")
        
        choice = self.get_user_choice("Choose format (1-3): ")
        format_map = {'1': 'csv', '2': 'json', '3': 'markdown'}
        export_format = format_map.get(choice)
        
        if not export_format:
            print(self.color.warning("⚠️  Invalid format choice"))
            return
        
        filename = self.get_user_choice(f"Output filename (with .{export_format} extension): ")
        if not filename:
            return
        
        tools = self.tool_manager.data_manager.data["tools"]
        
        try:
            if export_format == 'csv':
                export_csv(tools, Path(filename), self.color)
            elif export_format == 'json':
                export_json(tools, Path(filename), self.color)
            elif export_format == 'markdown':
                export_markdown(tools, Path(filename), self.color)
        except Exception as e:
            print(self.color.error(f"❌ Export failed: {e}"))
    
    def verify_tools_menu(self):
        """Verify tools menu."""
        print(self.color.highlight("\n🔍 Verify Tools"))
        print("─" * 15)
        
        tools = self.tool_manager.data_manager.data["tools"]
        verified_count = 0
        failed_count = 0
        
        print("Verifying tool paths...")
        for tool in tools:
            path_exists = Path(tool['path']).exists()
            if path_exists != tool.get('verified', False):
                tool['verified'] = path_exists
                tool['verification_date'] = datetime.now(timezone.utc).isoformat()
            
            if path_exists:
                verified_count += 1
            else:
                failed_count += 1
                print(f"❌ {tool['name']}: {tool['path']} not found")
        
        self.tool_manager.data_manager.save_data()
        print(f"\n✅ Verification complete: {verified_count} verified, {failed_count} failed")
    
    def settings_menu(self):
        """Settings menu."""
        print(self.color.highlight("\n⚙️  Settings"))
        print("─" * 10)
        print("Settings configuration is stored in config/settings.json")
        print("Edit the file directly to modify settings")
    
    def show_help(self):
        """Show help information."""
        help_text = f"""
{self.color.highlight(f'{APP_NAME} v{VERSION} - Help')}

{LEGEND}

📋 Menu Commands:
  1, a, add     - Add new tool
  2, s, search  - Search tools  
  3, u, update  - Update existing tool
  4, d, delete  - Delete tool
  5, l, list    - List all tools
  6, e, export  - Export data
  7, categories - List categories
  8, v, verify  - Verify tool paths
  9, settings   - Settings menu
  0, q, quit    - Exit application
  h, help       - Show this help

🔍 Search Types:
  • Fuzzy search - Find approximate matches
  • Exact search - Find exact matches
  • Regex search - Use regular expressions
  • Partial search - Find substring matches

💾 Data Storage:
  • Tools: data/tools.json
  • Backups: data/backups/
  • Config: config/settings.json

🎨 Colors:
  Set NO_COLOR environment variable to disable colors
        """
        print(help_text)

# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the application."""
    
    # Parse command line arguments
    parser = setup_cli_parser()
    args = parser.parse_args()

    # Initialize color manager
    color_enabled = not args.no_color
    color_manager = ColorManager(enabled=color_enabled)

    # Handle --show-legend flag immediately
    if args.show_legend:
        print(LEGEND)
        sys.exit(0)
    
    # Initialize data manager and tool manager
    data_manager = DataManager(color_manager=color_manager)
    tool_manager = ToolManager(data_manager)

    # Show legend on first run in interactive mode
    if not args.command and data_manager.is_new_data:
        print(color_manager.highlight("\n🌟 First Run Guide"))
        print(LEGEND)
        print(color_manager.info("Tip: Run with --show-legend anytime to see this guide"))

    elif (not args.command and data_manager.config.get("show_legend_on_start", True) and data_manager.is_new_data):
        print(LEGEND)
    
    # Determine mode of operation
    if args.interactive or (not args.command and len(sys.argv) == 1):
        # Interactive menu mode
        menu = MenuInterface(tool_manager)
        menu.run()
    elif args.command:
        # CLI mode
        data_manager.data["metadata"]["mode_usage"]["cli"] += 1
        success = handle_cli_command(args, tool_manager)
        data_manager.save_data()
        sys.exit(0 if success else 1)
    else:
        # Show help if no command provided
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

