"""Move all test files to tests directory"""
import os
import shutil
from pathlib import Path

# Get current directory
root_dir = Path(__file__).parent

# Create tests directory if it doesn't exist
tests_dir = root_dir / "tests"
tests_dir.mkdir(exist_ok=True)

# Find all test files in root directory
test_files = list(root_dir.glob("test*.py"))
test_files.extend(list(root_dir.glob("*test*.py")))

# Also check examples directory
examples_dir = root_dir / "examples"
if examples_dir.exists():
    test_files.extend(list(examples_dir.glob("*test*.py")))

# Move files
moved = []
skipped = []

for file in test_files:
    if file.parent == tests_dir:
        # Already in tests directory
        continue

    dest = tests_dir / file.name
    try:
        shutil.move(str(file), str(dest))
        moved.append(file.name)
        print(f"Moved: {file.name}")
    except Exception as e:
        skipped.append((file.name, str(e)))
        print(f"Skipped {file.name}: {e}")

print(f"\nSummary: {len(moved)} files moved, {len(skipped)} skipped")

# Create __init__.py in tests directory
init_file = tests_dir / "__init__.py"
if not init_file.exists():
    init_file.write_text("")
    print("Created tests/__init__.py")
