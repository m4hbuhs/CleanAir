import os
import re

print('--- CHECKING ST.PAGE_LINK REFERENCES ---')
broken = 0
for root, dirs, files in os.walk('.'):
    if '.venv' in root or '__pycache__' in root or '.git' in root:
        continue
    for f in files:
        if not f.endswith('.py'): continue
        filepath = os.path.join(root, f)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            links = re.findall(r'st\.page_link\([\'"]([^\'"]+)[\'"]', content)
            for link in links:
                if not os.path.exists(link):
                    print(f'BROKEN LINK in {filepath}: {link}')
                    broken += 1

if broken == 0:
    print('✅ All st.page_link references are valid and exist on disk.')

print('\n--- FINAL DIRECTORY LAYOUT (PAGES) ---')
def print_tree(directory, prefix=''):
    items = sorted(os.listdir(directory))
    for index, item in enumerate(items):
        if item == '__pycache__': continue
        path = os.path.join(directory, item)
        is_last = (index == len(items) - 1)
        print(prefix + ('└── ' if is_last else '├── ') + item)
        if os.path.isdir(path):
            print_tree(path, prefix + ('    ' if is_last else '│   '))

print('pages/')
print_tree('pages')
