import sqlite3

conn = sqlite3.connect('metadata.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

category = 'running'
group = 'the sole'

cursor.execute('''
    SELECT category, group_name, date, date_detected
    FROM sessions
    WHERE LOWER(TRIM(category)) = ? AND LOWER(TRIM(group_name)) = ?
''', (category.lower().strip(), group.lower().strip()))

rows = cursor.fetchall()

print(f'\nFound {len(rows)} matching sessions for "{category}" / "{group}":')
for row in rows:
    print(f"  - Category: '{row['category']}'")
    print(f"    Group: '{row['group_name']}'")
    print(f"    Date: {row['date']}")
    print(f"    Date Source: {row['date_detected']}")
    print()

conn.close()
