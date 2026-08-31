import os
import re

template_dir = 'templates'

for filename in os.listdir(template_dir):
    if not filename.endswith('.html'):
        continue
    path = os.path.join(template_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Fix: 's' if X != 1  ->  {% if X != 1 %}s{% endif %}
    def replace_plural(m):
        suffix = m.group(1)
        condition = m.group(2).strip()
        return '{%% if %s != 1 %%}%s{%% endif %%}' % (condition, suffix)

    content = re.sub(
        r"'([a-z]+)' if ([^}%]+?) != 1",
        replace_plural,
        content
    )

    # Fix tojson filter (Django doesn't have it; we'll use |safe with pre-serialized data)
    content = content.replace('| tojson', '|safe')

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed: {filename}')
    else:
        print(f'Clean: {filename}')
