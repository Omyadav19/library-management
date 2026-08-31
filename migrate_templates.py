import os
import re

template_dir = 'templates'
for filename in os.listdir(template_dir):
    if not filename.endswith('.html'): continue
    path = os.path.join(template_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add load static if base
    if filename == 'base.html':
        content = '{% load static %}\n' + content
        content = content.replace(
            '{% with messages = get_flashed_messages(with_categories=true) %}',
            '{% if messages %}'
        )
        content = content.replace(
            '{% if messages %}\n    {% for category, message in messages %}',
            '{% for message in messages %}'
        )
        content = content.replace(
            '<div data-toast data-type="{{ category }}" data-message="{{ message }}" style="display:none"></div>',
            '<div data-toast data-type="{{ message.tags }}" data-message="{{ message }}" style="display:none"></div>'
        )
        content = content.replace(
            '{% endfor %}\n  {% endif %}\n{% endwith %}',
            '{% endfor %}\n{% endif %}'
        )
        
    content = content.replace('request.endpoint', 'request.resolver_match.url_name')
    
    # Replace url_for('static', filename='...')
    content = re.sub(r"\{\{ url_for\('static', filename='(.+?)'\) \}\}", r"{% static '\1' %}", content)
    
    # Replace url_for('route_name')
    content = re.sub(r"\{\{ url_for\('([a-zA-Z0-9_]+)'\) \}\}", r"{% url '\1' %}", content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('Templates updated')
