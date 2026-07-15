import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Add import if not present
    if "from app.logger import logger" not in content and "logger" not in content[:200]:
        # find the last import and add it after
        lines = content.split('\n')
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import = i
        
        lines.insert(last_import + 1, "from app.logger import logger")
        content = '\n'.join(lines)

    # Replace print(f"[Tag] message") with logger.info(f"message") or error/warning
    # Regex to catch print statements
    def replacer(match):
        indent = match.group(1)
        inner = match.group(2)
        
        # Determine log level
        level = "info"
        lower_inner = inner.lower()
        if "error" in lower_inner or "fail" in lower_inner:
            level = "error"
        elif "warning" in lower_inner or "rate limit" in lower_inner or "exhausted" in lower_inner:
            level = "warning"

        # Remove the [Tag] prefix if it exists
        # e.g. f"[Classifier] message" -> f"message"
        inner = re.sub(r'f"\[.*?\]\s*', 'f"', inner)
        inner = re.sub(r'"\[.*?\]\s*', '"', inner)
        inner = re.sub(r"f'\[.*?\]\s*", "f'", inner)
        inner = re.sub(r"'\[.*?\]\s*", "'", inner)

        return f"{indent}logger.{level}({inner})"

    new_content = re.sub(r'^(\s*)print\((.*)\)$', replacer, content, flags=re.MULTILINE)

    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, _, files in os.walk('backend/app'):
    for f in files:
        if f.endswith('.py') and f not in ('logger.py', 'main.py', 'database.py'):
            process_file(os.path.join(root, f))
