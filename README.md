# ToolWiki

A dual-mode Python tool for managing and documenting installed tools in Kali Linux environments.

## Features

- **Dual Mode Operation**: Interactive menu mode and CLI mode with flags
- **Comprehensive Search**: Fuzzy search, regex patterns, multi-field filtering
- **Data Export**: CSV, JSON, Markdown formats
- **Tool Categorization**: Dynamic categories and tagging system
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Data Safety**: Automatic backups and validation
- **Color Support**: Customizable themes with accessibility options

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the tool:
```bash
# Interactive mode
python toolwiki.py

# CLI mode examples
python toolwiki.py add -n "nmap" -p "/usr/bin/nmap" -d "Network scanner"
python toolwiki.py search -n "nmap" --fuzzy
python toolwiki.py list --category network
python toolwiki.py export -f csv -o backup.csv
```

## CLI Usage

### Add Tools
```bash
toolwiki add -n "tool_name" -p "/path/to/tool" -d "description" -c "category"
```

### Search Tools
```bash
toolwiki search -n "name" --fuzzy
toolwiki search -d "keyword" --regex
toolwiki search -c "category" -t "tag1,tag2"
```

### List and Filter
```bash
toolwiki list --category network --sort name
toolwiki list --tags security,scanner --limit 10
```

### Export Data
```bash
toolwiki export -f csv -o tools.csv
toolwiki export -f markdown --filter "category=network"
```

## Interactive Mode

Launch without arguments to enter interactive mode with guided menus and real-time search.

## Configuration

Edit `config/settings.json` to customize:
- Default colors and themes
- Search behavior
- Backup settings
- UI preferences

## Data Structure

Tools are stored in `data/tools.json` with automatic backups in `data/backups/`.

## Legend
```
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
```

## FAQ

**Q: Why are there two options to run the tool?**

A: The tool supports both an interactive menu mode for guided use and a pure CLI mode with flags for automation and scripting flexibility.

**Q: What is the difference between categories and tags?**

A: Categories are broader classifications for tools, while tags provide more granular, flexible labeling to help organize and search tools effectively.

**Q: Why use this tool?**

A: Kali Tool Wiki helps you maintain a clear, searchable, and documented list of your installed tools, ensuring you never forget their purpose or usage, especially in custom Kali Linux environments.

**Q: How can I contribute or suggest improvements?**

A: Contributions and suggestions are welcome! Please open issues or pull requests on the project's GitHub repository to help improve the tool.

## License

MIT License - Personal and educational use
