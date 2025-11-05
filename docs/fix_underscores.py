import re

# Read the file
with open('technical_documentation.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# Function to fix underscores in \texttt{} commands
def fix_texttt(match):
    inner_text = match.group(1)
    # Replace _ with \textunderscore only if not already escaped
    fixed_text = re.sub(r'(?<!\\)_', r'\\textunderscore ', inner_text)
    return r'\texttt{' + fixed_text + '}'

# Replace all \texttt{...} with fixed versions
content = re.sub(r'\\texttt\{([^}]*)\}', fix_texttt, content)

# Write back
with open('technical_documentation.tex', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all underscores in \\texttt{} commands!")
