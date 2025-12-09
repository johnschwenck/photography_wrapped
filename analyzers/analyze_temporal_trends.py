"""
Temporal Trend Analysis for The Sole Run Club
Generates insights about how photography evolved over time in 2025
"""
import sqlite3
import re
from collections import defaultdict

def analyze_temporal_trends(db_path='metadata.db', category='running', group='thesole'):
    """Analyze temporal trends for The Sole photography."""
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Pattern to extract dates from session names (format: "XX_-_YYYY-MM-DD")
    date_pattern = r'(\d{4}-\d{2}-\d{2})'
    
    print("=" * 80)
    print("THE SOLE 2025: TEMPORAL TRENDS ANALYSIS")
    print("=" * 80)
    print()
    
    # 1. Hit Rate Progression Over Time
    print("HIT RATE PROGRESSION")
    print("-" * 80)
    
    sessions = conn.execute("""
        SELECT name, hit_rate, total_photos, total_raw_photos
        FROM sessions
        WHERE category = ? AND group_name = ?
        ORDER BY name
    """, (category, group)).fetchall()
    
    sessions_with_dates = []
    for session in sessions:
        match = re.search(date_pattern, session['name'])
        if match:
            sessions_with_dates.append({
                'name': session['name'],
                'date': match.group(1),
                'hit_rate': session['hit_rate'],
                'edited': session['total_photos'],
                'raw': session['total_raw_photos']
            })
    
    if sessions_with_dates:
        sessions_with_dates.sort(key=lambda x: x['date'])
        print(f"\nTotal Sessions: {len(sessions_with_dates)}")
        print(f"Date Range: {sessions_with_dates[0]['date']} to {sessions_with_dates[-1]['date']}")
        print()
        
        monthly_hit_rates = defaultdict(list)
        for session in sessions_with_dates:
            if session['hit_rate']:
                month = session['date'][:7]
                monthly_hit_rates[month].append(session['hit_rate'])
        
        print("Monthly Average Hit Rate:")
        for month in sorted(monthly_hit_rates.keys()):
            avg = sum(monthly_hit_rates[month]) / len(monthly_hit_rates[month])
            print(f"  {month}: {avg:.2f}% ({len(monthly_hit_rates[month])} sessions)")
        
        q1 = [s for s in sessions_with_dates if s['date'] < '2025-04' and s['hit_rate']]
        q4 = [s for s in sessions_with_dates if s['date'] >= '2025-10' and s['hit_rate']]
        
        if q1 and q4:
            q1_avg = sum(s['hit_rate'] for s in q1) / len(q1)
            q4_avg = sum(s['hit_rate'] for s in q4) / len(q4)
            print()
            print(f"Q1 Average: {q1_avg:.2f}%")
            print(f"Q4 Average: {q4_avg:.2f}%")
            print(f"Improvement: {q4_avg - q1_avg:+.2f} percentage points")
    
    print("\n")
    
    # 2. Lens Usage Evolution
    print("LENS USAGE EVOLUTION")
    print("-" * 80)
    
    lens_data = conn.execute("""
        SELECT s.name, p.lens_name, COUNT(*) as count
        FROM photos p
        JOIN sessions s ON p.session_id = s.id
        WHERE s.category = ? AND s.group_name = ?
        GROUP BY s.name, p.lens_name
    """, (category, group)).fetchall()
    
    monthly_lens = defaultdict(lambda: defaultdict(int))
    monthly_totals = defaultdict(int)
    
    for row in lens_data:
        match = re.search(date_pattern, row['name'])
        if match:
            month = match.group(1)[:7]
            monthly_lens[month][row['lens_name']] += row['count']
            monthly_totals[month] += row['count']
    
    print("\nMost Used Lens Each Month:")
    for month in sorted(monthly_lens.keys()):
        top_lens = max(monthly_lens[month].items(), key=lambda x: x[1])
        pct = (top_lens[1] / monthly_totals[month] * 100)
        print(f"  {month}: {top_lens[0]} - {top_lens[1]} photos ({pct:.1f}%)")
    
    print("\n85mm F1.4 GM II Usage Over Time:")
    for month in sorted(monthly_lens.keys()):
        count = monthly_lens[month].get('FE 85mm F1.4 GM II', 0)
        pct = (count / monthly_totals[month] * 100) if monthly_totals[month] > 0 else 0
        print(f"  {month}: {count} photos ({pct:.1f}%)")
    
    print("\n")
    
    # 3. ISO Trends
    print("ISO TRENDS")
    print("-" * 80)
    
    iso_data = conn.execute("""
        SELECT s.name, AVG(p.iso) as avg_iso, COUNT(*) as count
        FROM photos p
        JOIN sessions s ON p.session_id = s.id
        WHERE s.category = ? AND s.group_name = ?
          AND p.iso < 65535 AND p.iso IS NOT NULL
        GROUP BY s.name
    """, (category, group)).fetchall()
    
    monthly_iso = defaultdict(lambda: {'total_iso': 0, 'count': 0})
    for row in iso_data:
        match = re.search(date_pattern, row['name'])
        if match:
            month = match.group(1)[:7]
            monthly_iso[month]['total_iso'] += row['avg_iso'] * row['count']
            monthly_iso[month]['count'] += row['count']
    
    print("\nAverage ISO by Month:")
    for month in sorted(monthly_iso.keys()):
        avg = monthly_iso[month]['total_iso'] / monthly_iso[month]['count']
        print(f"  {month}: ISO {avg:.0f} ({monthly_iso[month]['count']} photos)")
    
    high_iso_data = conn.execute("""
        SELECT s.name,
               COUNT(*) as high_iso,
               (SELECT COUNT(*) FROM photos WHERE session_id = s.id) as total
        FROM photos p
        JOIN sessions s ON p.session_id = s.id
        WHERE s.category = ? AND s.group_name = ?
          AND p.iso >= 3200 AND p.iso IS NOT NULL
        GROUP BY s.name
    """, (category, group)).fetchall()
    
    monthly_high_iso = defaultdict(lambda: {'high': 0, 'total': 0})
    for row in high_iso_data:
        match = re.search(date_pattern, row['name'])
        if match:
            month = match.group(1)[:7]
            monthly_high_iso[month]['high'] += row['high_iso']
            monthly_high_iso[month]['total'] += row['total']
    
    print("\nHigh ISO (3200+) Usage Over Time:")
    for month in sorted(monthly_high_iso.keys()):
        data = monthly_high_iso[month]
        pct = (data['high'] / data['total'] * 100) if data['total'] > 0 else 0
        print(f"  {month}: {data['high']}/{data['total']} photos ({pct:.1f}%)")
    
    print("\n")
    
    # 4. Shutter Speed Evolution
    print("SHUTTER SPEED EVOLUTION")
    print("-" * 80)
    
    shutter_data = conn.execute("""
        SELECT s.name, p.shutter_speed, COUNT(*) as count
        FROM photos p
        JOIN sessions s ON p.session_id = s.id
        WHERE s.category = ? AND s.group_name = ?
        GROUP BY s.name, p.shutter_speed
    """, (category, group)).fetchall()
    
    monthly_shutter = defaultdict(lambda: defaultdict(int))
    for row in shutter_data:
        match = re.search(date_pattern, row['name'])
        if match:
            month = match.group(1)[:7]
            monthly_shutter[month][row['shutter_speed']] += row['count']
    
    print("\nMost Used Shutter Speed Each Month:")
    for month in sorted(monthly_shutter.keys()):
        speeds = monthly_shutter[month]
        top_speed = max(speeds.items(), key=lambda x: x[1])
        total = sum(speeds.values())
        pct = (top_speed[1] / total * 100) if total > 0 else 0
        print(f"  {month}: {top_speed[0]} - {top_speed[1]} photos ({pct:.1f}%)")
    
    print("\n")
    
    # 5. Aperture Evolution
    print("APERTURE EVOLUTION")
    print("-" * 80)
    
    aperture_data = conn.execute("""
        SELECT s.name,
               COUNT(CASE WHEN p.aperture IN (1.4, 1.8) THEN 1 END) as wide_open,
               COUNT(*) as total
        FROM photos p
        JOIN sessions s ON p.session_id = s.id
        WHERE s.category = ? AND s.group_name = ?
        GROUP BY s.name
    """, (category, group)).fetchall()
    
    monthly_aperture = defaultdict(lambda: {'wide': 0, 'total': 0})
    for row in aperture_data:
        match = re.search(date_pattern, row['name'])
        if match:
            month = match.group(1)[:7]
            monthly_aperture[month]['wide'] += row['wide_open']
            monthly_aperture[month]['total'] += row['total']
    
    print("\nWide Open (f/1.4 or f/1.8) Usage:")
    for month in sorted(monthly_aperture.keys()):
        data = monthly_aperture[month]
        pct = (data['wide'] / data['total'] * 100) if data['total'] > 0 else 0
        print(f"  {month}: {data['wide']}/{data['total']} photos ({pct:.1f}%)")
    
    print("\n")
    
    # 6. Session Activity
    print("SESSION ACTIVITY")
    print("-" * 80)
    
    all_sessions = conn.execute("""
        SELECT name, total_photos
        FROM sessions
        WHERE category = ? AND group_name = ?
    """, (category, group)).fetchall()
    
    monthly_activity = defaultdict(lambda: {'count': 0, 'photos': 0})
    for row in all_sessions:
        match = re.search(date_pattern, row['name'])
        if match:
            month = match.group(1)[:7]
            monthly_activity[month]['count'] += 1
            monthly_activity[month]['photos'] += row['total_photos']
    
    print("\nSessions and Photos per Month:")
    for month in sorted(monthly_activity.keys()):
        data = monthly_activity[month]
        avg = data['photos'] / data['count'] if data['count'] > 0 else 0
        print(f"  {month}: {data['count']} sessions, {data['photos']} photos (avg {avg:.0f} per session)")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)

if __name__ == "__main__":
    analyze_temporal_trends()
