import sqlite3
conn = sqlite3.connect('db.sqlite3')
res = conn.execute("SELECT sql FROM sqlite_master WHERE name='library_issuerecord'").fetchone()
print(res[0] if res else 'None')
