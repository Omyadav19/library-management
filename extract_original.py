import json
import re

lines = {}

with open('C:/Users/DELL 123/.gemini/antigravity-ide/brain/2affacb2-7fe9-44f6-8357-6a3275610aa4/.system_generated/logs/transcript_full.jsonl', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            obj = json.loads(line.strip())
            if 'content' in obj and 'File Path: `file:///d:/library_management/library/views.py`' in obj['content']:
                c = obj['content']
                if 'pymongo' not in c:
                    for l in c.split('\n'):
                        m = re.match(r'^(\d+):\s(.*)$', l)
                        if m:
                            lines[int(m.group(1))] = m.group(2)
        except Exception as e:
            pass

with open('library/views.py', 'w', encoding='utf-8') as out:
    for i in sorted(lines.keys()):
        if i <= 557:
            out.write(lines[i] + '\n')
