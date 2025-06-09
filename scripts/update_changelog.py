import json
import os
from datetime import date

# Paths
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pkg_path = os.path.join(root, "package.json")
changelog_path = os.path.join(root, "CHANGELOG.md")

# Get version
with open(pkg_path, "r", encoding="utf-8") as f:
    version = json.load(f).get("version", "unknown")

# Prepare new changelog entry
today = date.today().isoformat()
new_entry = f"## [{version}] - {today}\n- Update details here.\n\n"

# Read existing changelog
if os.path.exists(changelog_path):
    with open(changelog_path, "r", encoding="utf-8") as f:
        old_content = f.read()
else:
    old_content = "# Changelog\n\n"

# Insert new entry after the title
if old_content.startswith("# Changelog"):
    parts = old_content.split("\n", 2)
    if len(parts) > 2:
        new_content = f"{parts[0]}\n\n{new_entry}{parts[2]}"
    else:
        new_content = f"{parts[0]}\n\n{new_entry}"
else:
    new_content = f"# Changelog\n\n{new_entry}{old_content}"

# Write back
with open(changelog_path, "w", encoding="utf-8") as f:
    f.write(new_content)