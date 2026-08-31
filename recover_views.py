import json
import re

out = open('restored_views.py', 'w', encoding='utf-8')
with open('C:/Users/DELL 123/.gemini/antigravity-ide/brain/2affacb2-7fe9-44f6-8357-6a3275610aa4/.system_generated/logs/transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('type') == 'TOOL_RESPONSE' and 'views.py' in obj.get('content', '') and 'File Path: `file:///d:/library_management/library/views.py`' in obj.get('content', ''):
            content = obj.get('content')
            lines = content.split('\n')
            for l in lines:
                # Format is `<line_number>: <original_line>`
                m = re.match(r'^\d+:\s(.*)$', l)
                if m:
                    out.write(m.group(1) + '\n')
out.close()
