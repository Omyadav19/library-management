import os
import re

template_dir = 'templates'

def fix_content(content, filename):
    # 1) Fix broken `| length {% if ... %}s{% endif %}` patterns from bad prior fix
    #    Pattern: "| {% if VAR| | length != 1 %}s{% endif %}"
    #    These came from replacing `'s' if X != 1` when X was itself a filter expression
    #    e.g., `{{ books | length }} book{{ 's' if books | length != 1 }}`
    # We'll just hard-code fix the specific broken patterns
    content = re.sub(
        r'\|\s*\{%\s*if\s+(\w+)\|\s*\|\s*length\s*!=\s*1\s*%\}s\{%\s*endif\s*%\}',
        r'{% if \1.count != 1 %}s{% endif %}',
        content
    )
    # also handle: book{% if books| | length != 1 %}s{% endif %}
    content = re.sub(
        r'(\w+)\{%\s*if\s+(\w+)\|\s*\|\s*length\s*!=\s*1\s*%\}s\{%\s*endif\s*%\}',
        r'\1{% if \2|length != 1 %}s{% endif %}',
        content
    )
    # 2) Fix: `record.issue_id if record else ''` (Jinja2 inline if on the right of |)
    # In Django, use `{% if record %}{{ record.issue_id }}{% endif %}` but in attribute context
    # These appear as value="..." attributes — simplest fix is just use empty default
    content = re.sub(
        r"value=\"\{\{ record\.issue_id if record else '' \}\}\"",
        'value="{% if record %}{{ record.issue_id }}{% endif %}"',
        content
    )
    # 3) Fix inline ternary in overdue.html: 
    # `'{% if item.days_overdue != 1 %}s{% endif %}' from '{% if item.days_overdue != 1 %}s{% endif %}'`
    # This is a case where the pattern appears INSIDE a string context in a tag like:
    # badge-overdue">{{ item.days_overdue }} day{% if item.days_overdue != 1 %}s{% endif %} overdue
    # Actually the issue might be inside a CSS value or data attribute — let's check
    
    # 4) Fix `data.popular_books[0].issue_count` (Django doesn't support subscript)
    content = content.replace('data.popular_books[0].issue_count', 'data.popular_books.0.issue_count')
    
    # 5) Fix profile.currently_issued in string context inside a tag attribute
    # Pattern: 's' if ... != 1 which the fix turned into {% if ... %}s{% endif %} INSIDE an attribute
    # Those need to be outside the attribute or in a simpler form
    
    return content

for filename in os.listdir(template_dir):
    if not filename.endswith('.html'):
        continue
    path = os.path.join(template_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    content = fix_content(content, filename)
    
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed: {filename}')
    else:
        print(f'Unchanged: {filename}')
