import sqlite3

conn = sqlite3.connect('metadata.db')

print('=== DATABASE SUMMARY ===\n')

# Total counts
total_sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
total_photos_db = conn.execute('SELECT COUNT(*) FROM photos').fetchone()[0]

print(f'Total sessions in database: {total_sessions}')
print(f'Total photos in database: {total_photos_db}\n')

# Category breakdown
print('=== SESSIONS BY CATEGORY ===')
cats = conn.execute('''
    SELECT category, COUNT(*) as sessions, SUM(total_photos) as photos 
    FROM sessions 
    GROUP BY category
''').fetchall()
for c in cats:
    print(f'{c[0]}: {c[1]} sessions, {c[2]} photos')

# Group breakdown
print('\n=== SESSIONS BY GROUP ===')
groups = conn.execute('''
    SELECT group_name, COUNT(*) as sessions, SUM(total_photos) as photos 
    FROM sessions 
    GROUP BY group_name
''').fetchall()
for g in groups:
    print(f'{g[0]}: {g[1]} sessions, {g[2]} photos')

# Recent sessions
print('\n=== LAST 10 SESSIONS (most recent first) ===')
sessions = conn.execute('''
    SELECT id, name, category, group_name, total_photos, hit_rate, date 
    FROM sessions 
    ORDER BY id DESC 
    LIMIT 10
''').fetchall()
for s in sessions:
    print(f'ID: {s[0]}, Name: {s[1]}, Category: {s[2]}, Group: {s[3]}, Photos: {s[4]}, Hit Rate: {s[5]:.1f}%, Date: {s[6]}')

# Check for duplicates
print('\n=== DUPLICATE CHECK ===')
dupes = conn.execute('''
    SELECT name, COUNT(*) as count 
    FROM sessions 
    GROUP BY name 
    HAVING count > 1 
    ORDER BY count DESC
''').fetchall()
if dupes:
    print(f'Found {len(dupes)} duplicate session names:')
    for d in dupes:
        print(f'  "{d[0]}" appears {d[1]} times')
else:
    print('No duplicate session names found')

conn.close()
