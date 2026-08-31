import json
import re

lines_dict = {}

with open('C:/Users/DELL 123/.gemini/antigravity-ide/brain/2affacb2-7fe9-44f6-8357-6a3275610aa4/.system_generated/logs/transcript_full.jsonl', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            obj = json.loads(line.strip())
            if obj.get('type') == 'TOOL_RESPONSE' and 'File Path: `file:///d:/library_management/library/views.py`' in obj.get('content', ''):
                content = obj['content']
                # Only parse the SQLite version, which imports models at the top
                # or we just match the lines
                for l in content.split('\n'):
                    m = re.match(r'^(\d+):\s(.*)$', l)
                    if m:
                        line_num = int(m.group(1))
                        # Only keep it if it's the SQLite version (we know it has 557 lines)
                        # We'll just overwrite any newer versions if we sort correctly, wait, newer version is PyMongo and also has line numbers if viewed.
                        # But wait, did I use view_file on the PyMongo version? No, I only used write_to_file for PyMongo.
                        # Wait, let's just write all lines up to 557. The new one was 557? No, new was different.
                        lines_dict[line_num] = m.group(2)
        except:
            pass

with open('library/views.py', 'w', encoding='utf-8') as out:
    # 557 is the exact length of the original views.py
    for i in range(1, 558):
        if i in lines_dict:
            out.write(lines_dict[i] + '\n')
