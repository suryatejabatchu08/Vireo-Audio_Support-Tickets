import csv
from datetime import datetime, timedelta
from collections import defaultdict

# ---------- Configuration ----------
TICKETS_FILE = 'tickets_cleaned.csv'
AGENTS_FILE = 'agents.csv'

OUTPUT_SHIFT_CSV = 'weekly_shift_report.csv'
OUTPUT_AGENT_DETAIL_CSV = 'weekly_agent_report_detailed.csv'   # keep full detail
OUTPUT_AGENT_SUMMARY_CSV = 'weekly_agent_report_summary.csv'  # whole period summary (Tier1 only)
OUTPUT_AGENT_LAST4_SUMMARY_CSV = 'weekly_agent_report_last4weeks_summary.csv'  # last 4 weeks summary (Tier1 only)
OUTPUT_TIER2_NOT_COMPARABLE_CSV = 'tier2_not_comparable.csv'
OUTPUT_HTML = 'weekly_breach_report.html'

CHANNEL_TARGETS = {
    'chat': 15,        # minutes
    'voice': 120,      # 2 hours
    'social': 240,     # 4 hours
    'email': 480       # 8 hours
}

FRONTLINE_TEAM_BY_CHANNEL = {
    'chat': 'Chat Frontline',
    'social': 'Chat Frontline',
    'email': 'Email Frontline',
    'voice': 'Voice Frontline'
}

SHIFT_DEFS = {
    'Morning': (6*60, 14*60),   # 06:00-14:00
    'Day':   (14*60, 22*60),    # 14:00-22:00
    'Night': (22*60, 24*60, 0*60, 6*60)  # 22:00-24:00 and 00:00-06:00
}

def time_to_minutes(t_str):
    try:
        h, m = map(int, t_str.split(':'))
        return h*60 + m
    except:
        return None

def get_shift_from_time(time_str):
    mins = time_to_minutes(time_str)
    if mins is None:
        return None
    if 6*60 <= mins < 14*60:
        return 'Morning'
    if 14*60 <= mins < 22*60:
        return 'Day'
    return 'Night'

def parse_date_only(dt_str):
    try:
        return datetime.strptime(dt_str[:10], '%Y-%m-%d').date()
    except:
        return None

def parse_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
    except:
        return None

# ---------- Load agents ----------
agents_rows = []
with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        agents_rows.append(row)

for r in agents_rows:
    r['from_date'] = datetime.strptime(r['from_date'], '%Y-%m-%d').date() if r['from_date'] else None
    r['to_date'] = datetime.strptime(r['to_date'], '%Y-%m-%d').date() if r['to_date'] else None

agents_by_id = defaultdict(list)
for r in agents_rows:
    agents_by_id[r['agent_id']].append(r)
for aid in agents_by_id:
    agents_by_id[aid].sort(key=lambda x: x['from_date'] or datetime.min.date(), reverse=True)

def get_agent_row(agent_id, target_date):
    for r in agents_by_id.get(agent_id, []):
        if r['from_date'] and (r['to_date'] is None or target_date <= r['to_date']):
            if target_date >= r['from_date']:
                return r
    return None

def has_coverage(required_team, target_date, shift):
    for r in agents_rows:
        if r['team'] == required_team and r['shift'] == shift:
            if r['from_date'] and (r['to_date'] is None or target_date <= r['to_date']):
                if target_date >= r['from_date']:
                    return True
    return False

# ---------- Process tickets ----------
shift_week = defaultdict(lambda: defaultdict(lambda: {
    'tickets':0, 'no_cover':0, 'staffed_late':0
}))
agent_week = defaultdict(lambda: defaultdict(lambda: {
    'tickets':0, 'no_cover':0, 'staffed_late':0,
    'agent_name':'', 'team':''
}))

with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticket_id = row['ticket_id']
        created_str = row['created_at']
        first_str = row['first_response_at']
        channel = row['channel'].strip().lower()
        agent_id = row['agent_id']

        created_dt = parse_datetime(created_str)
        first_dt = parse_datetime(first_str)
        if created_dt is None:
            continue

        created_date = created_dt.date()
        week_start = created_date - timedelta(days=created_date.weekday())  # Monday

        shift = get_shift_from_time(created_str[11:16])
        if shift is None:
            continue

        breach = False
        cause = None
        response_minutes = None
        if first_dt is not None:
            diff = first_dt - created_dt
            response_minutes = diff.total_seconds() / 60.0
            if response_minutes >= 0:
                target = CHANNEL_TARGETS.get(channel)
                if target is not None and response_minutes > target:
                    breach = True
                    required_team = FRONTLINE_TEAM_BY_CHANNEL.get(channel)
                    if required_team is not None:
                        if has_coverage(required_team, created_date, shift):
                            cause = 'staffed_late'
                        else:
                            cause = 'no_cover'
                    else:
                        cause = 'staffed_late'  # unknown channel fallback

        # Update shift stats
        sw = shift_week[week_start][shift]
        sw['tickets'] += 1
        if breach:
            if cause == 'no_cover':
                sw['no_cover'] += 1
            elif cause == 'staffed_late':
                sw['staffed_late'] += 1

        # Agent stats
        agent_row = get_agent_row(agent_id, created_date)
        if agent_row is not None:
            agg = agent_week[week_start][agent_id]
            agg['tickets'] += 1
            if breach:
                if cause == 'no_cover':
                    agg['no_cover'] += 1
                elif cause == 'staffed_late':
                    agg['staffed_late'] += 1
            agg['agent_name'] = agent_row['name']
            agg['team'] = agent_row['team']

# ---------- Write shift CSV with total_breaches and partial_week ----------
# Determine max week for partial marking
all_weeks = sorted(shift_week.keys())
final_week = all_weeks[-1] if all_weeks else None

with open(OUTPUT_SHIFT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['week_start', 'shift', 'tickets', 'no_cover_breaches', 'staffed_late_breaches', 'total_breaches', 'breach_rate_%', 'partial_week'])
    for week_start in all_weeks:
        for shift in ['Morning', 'Day', 'Night']:
            data = shift_week[week_start].get(shift, {'tickets':0, 'no_cover':0, 'staffed_late':0})
            tickets = data['tickets']
            no_cover = data['no_cover']
            staffed_late = data['staffed_late']
            total_breaches = no_cover + staffed_late
            rate = (total_breaches / tickets * 100) if tickets > 0 else 0.0
            partial = 'YES' if week_start == final_week else ''
            writer.writerow([week_start, shift, tickets, no_cover, staffed_late, total_breaches, f"{rate:.2f}", partial])

# ---------- Agent detailed CSV ----------
with open(OUTPUT_AGENT_DETAIL_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['week_start', 'agent_id', 'agent_name', 'team', 'tickets', 'breaches',
                     'breach_rate_%', 'no_cover_breaches', 'staffed_late_breaches'])
    for week_start in sorted(agent_week.keys()):
        for agent_id, data in agent_week[week_start].items():
            tickets = data['tickets']
            no_cover = data['no_cover']
            staffed_late = data['staffed_late']
            breaches = no_cover + staffed_late
            rate = (breaches / tickets * 100) if tickets > 0 else 0.0
            writer.writerow([
                week_start, agent_id, data['agent_name'], data['team'],
                tickets, breaches, f"{rate:.2f}",
                no_cover, staffed_late
            ])

# ---------- Agent summaries (Tier1 only) ----------
def is_tier1(team):
    return team != 'Escalations & Warranty'

agent_total = defaultdict(lambda: {
    'tickets':0, 'no_cover':0, 'staffed_late':0,
    'agent_name':'', 'team':''
})
for week_start, week_data in agent_week.items():
    for agent_id, data in week_data.items():
        if not is_tier1(data['team']):
            continue
        tot = agent_total[agent_id]
        tot['tickets'] += data['tickets']
        tot['no_cover'] += data['no_cover']
        tot['staffed_late'] += data['staffed_late']
        if tot['agent_name'] == '':
            tot['agent_name'] = data['agent_name']
            tot['team'] = data['team']

# Whole period summary (Tier1)
with open(OUTPUT_AGENT_SUMMARY_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['agent_id', 'agent_name', 'team', 'tickets', 'breaches',
                     'breach_rate_%', 'staffed_late_rate_%', 'no_cover_breaches', 'staffed_late_breaches', 'mostly_inherited_flag'])
    for agent_id, data in agent_total.items():
        if data['tickets'] < 20:
            continue  # skip agents with less than 20 tickets
        tickets = data['tickets']
        no_cover = data['no_cover']
        staffed_late = data['staffed_late']
        breaches = no_cover + staffed_late
        breach_rate = (breaches / tickets * 100)
        staffed_late_rate = (staffed_late / tickets * 100) if tickets > 0 else 0.0
        mostly = 'YES' if breaches > 0 and (no_cover / breaches) > 0.5 else 'NO'
        writer.writerow([
            agent_id, data['agent_name'], data['team'],
            tickets,
            breaches,
            f"{breach_rate:.2f}",
            f"{staffed_late_rate:.2f}",
            no_cover,
            staffed_late,
            mostly
        ])

# Last 4 weeks summary (Tier1)
if agent_week:
    max_week = max(agent_week.keys())
    cutoff_week = max_week - timedelta(weeks=3)  # inclusive
else:
    max_week = datetime.min.date()
    cutoff_week = datetime.min.date()

agent_last4 = defaultdict(lambda: {
    'tickets':0, 'no_cover':0, 'staffed_late':0,
    'agent_name':'', 'team':''
})
for week_start, week_data in agent_week.items():
    if week_start >= cutoff_week:
        for agent_id, data in week_data.items():
            if not is_tier1(data['team']):
                continue
            tot = agent_last4[agent_id]
            tot['tickets'] += data['tickets']
            tot['no_cover'] += data['no_cover']
            tot['staffed_late'] += data['staffed_late']
            if tot['agent_name'] == '':
                tot['agent_name'] = data['agent_name']
                tot['team'] = data['team']

with open(OUTPUT_AGENT_LAST4_SUMMARY_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['agent_id', 'agent_name', 'team', 'tickets', 'breaches',
                     'breach_rate_%', 'staffed_late_rate_%', 'no_cover_breaches', 'staffed_late_breaches', 'mostly_inherited_flag'])
    for agent_id, data in agent_last4.items():
        if data['tickets'] < 20:
            continue
        tickets = data['tickets']
        no_cover = data['no_cover']
        staffed_late = data['staffed_late']
        breaches = no_cover + staffed_late
        breach_rate = (breaches / tickets * 100)
        staffed_late_rate = (staffed_late / tickets * 100) if tickets > 0 else 0.0
        mostly = 'YES' if breaches > 0 and (no_cover / breaches) > 0.5 else 'NO'
        writer.writerow([
            agent_id, data['agent_name'], data['team'],
            tickets,
            breaches,
            f"{breach_rate:.2f}",
            f"{staffed_late_rate:.2f}",
            no_cover,
            staffed_late,
            mostly
        ])

# ---------- Tier2 agents to separate file ----------
tier2_agents = set()
for week_start, week_data in agent_week.items():
    for agent_id, data in week_data.items():
        if data['team'] == 'Escalations & Warranty':
            tier2_agents.add((agent_id, data['agent_name']))

with open(OUTPUT_TIER2_NOT_COMPARABLE_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['note'])
    writer.writerow(['Escalations & Warranty agents are not comparable on per‑ticket first‑response basis; see policy.'])
    writer.writerow(['agent_id', 'agent_name'])
    for agent_id, name in sorted(tier2_agents):
        writer.writerow([agent_id, name])

# ---------- HTML report ----------
# Last 8 weeks by shift with cause split
last_8_weeks = all_weeks[-8:] if len(all_weeks) >= 8 else all_weeks

# Top 10 Tier1 agents by staffed-late breach rate (>=20 tickets)
tier1_agents_with_rate = []
for agent_id, data in agent_total.items():
    if data['tickets'] < 20:
        continue
    tickets = data['tickets']
    staffed_late = data['staffed_late']
    rate = (staffed_late / tickets * 100) if tickets > 0 else 0.0
    tier1_agents_with_rate.append((agent_id, data, rate))
top_by_staffed_late = sorted(tier1_agents_with_rate, key=lambda x: x[2], reverse=True)[:10]

html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Weekly Breach Report</title>
    <style>
        table {{border-collapse: collapse; width: 100%; margin-bottom: 20px;}}
        th, td {{border: 1px solid #ddd; padding: 8px; text-align: left;}}
        th {{background-color: #f2f2f2;}}
        .summary {{margin-bottom: 30px;}}
    </style>
</head>
<body>
    <h1>Weekly Breach Report</h1>
    <p><em>Agent figures show who resolved the ticket, not who sent the first reply, because the helpdesk does not record that.</em></p>

    <div class="summary">
        <h2>Last 8 Weeks by Shift (with cause split)</h2>
        <table>
            <tr>
                <th>Week Start</th><th>Shift</th><th>Tickets</th><th>No‑Cover Breaches</th><th>Staffed‑Late Breaches</th><th>Total Breaches</th><th>Breach Rate (%)</th><th>Partial Week</th>
            </tr>
"""
for week_start in last_8_weeks:
    for shift in ['Morning', 'Day', 'Night']:
        data = shift_week[week_start].get(shift, {'tickets':0, 'no_cover':0, 'staffed_late':0})
        tickets = data['tickets']
        no_cover = data['no_cover']
        staffed_late = data['staffed_late']
        total_breaches = no_cover + staffed_late
        rate = (total_breaches / tickets * 100) if tickets > 0 else 0.0
        partial = 'YES' if week_start == final_week else ''
        html_content += f"""
            <tr>
                <td>{week_start}</td><td>{shift}</td><td>{tickets}</td><td>{no_cover}</td><td>{staffed_late}</td><td>{total_breaches}</td><td>{rate:.2f}</td><td>{partial}</td>
            </tr>
"""
html_content += """
        </table>
    </div>

    <div class="summary">
        <h2>Top 10 Tier 1 Agents by Staffed‑Late Breach Rate (min 20 tickets)</h2>
        <table>
            <tr>
                <th>Agent ID</th><th>Agent Name</th><th>Team</th><th>Tickets</th><th>Breaches</th><th>Breach Rate (%)</th><th>Staffed‑Late Rate (%)</th><th>No‑Cover Breaches</th><th>Staffed‑Late Breaches</th><th>Mostly Inherited</th>
            </tr>
"""
for agent_id, data, rate in top_by_staffed_late:
    tickets = data['tickets']
    no_cover = data['no_cover']
    staffed_late = data['staffed_late']
    breaches = no_cover + staffed_late
    breach_rate = (breaches / tickets * 100)
    staffed_late_rate = (staffed_late / tickets * 100) if tickets > 0 else 0.0
    mostly = 'YES' if breaches > 0 and (no_cover / breaches) > 0.5 else 'NO'
    html_content += f"""
            <tr>
                <td>{agent_id}</td><td>{data['agent_name']}</td><td>{data['team']}</td><td>{tickets}</td><td>{breaches}</td><td>{breach_rate:.2f}</td><td>{staffed_late_rate:.2f}</td><td>{no_cover}</td><td>{staffed_late}</td><td>{mostly}</td>
            </tr>
"""
html_content += """
        </table>
    </div>

    <p>For full detail, see the CSV files:</p>
    <ul>
        <li><code>weekly_shift_report.csv</code> – weekly shift table with cause split and total breaches</li>
        <li><code>weekly_agent_report_detailed.csv</code> – weekly agent‑level detail (all agents, all weeks)</li>
        <li><code>weekly_agent_report_summary.csv</code> – agent summary over whole period (Tier 1, min 20 tickets)</li>
        <li><code>weekly_agent_report_last4weeks_summary.csv</code> – agent summary over last 4 weeks (Tier 1, min 20 tickets)</li>
        <li><code>tier2_not_comparable.csv</code> – list of Escalations & Warranty agents with explanatory note</li>
    </ul>
</body>
</html>
"""

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"Shift report written to {OUTPUT_SHIFT_CSV}")
print(f"Agent detailed report written to {OUTPUT_AGENT_DETAIL_CSV}")
print(f"Agent summary (whole period) written to {OUTPUT_AGENT_SUMMARY_CSV}")
print(f"Agent summary (last 4 weeks) written to {OUTPUT_AGENT_LAST4_SUMMARY_CSV}")
print(f"Tier2 not comparable written to {OUTPUT_TIER2_NOT_COMPARABLE_CSV}")
print(f"HTML report written to {OUTPUT_HTML}")

# ---------- Compute Tier 1 average staffed-late rate and highest three agents ----------
tier1_staffed_late_rates = []
for agent_id, data in agent_total.items():
    if data['tickets'] < 20:
        continue
    tickets = data['tickets']
    staffed_late = data['staffed_late']
    rate = (staffed_late / tickets * 100) if tickets > 0 else 0.0
    tier1_staffed_late_rates.append((agent_id, data['agent_name'], data['team'], tickets, staffed_late, rate))

if tier1_staffed_late_rates:
    avg_rate = sum(rate for _, _, _, _, _, rate in tier1_staffed_late_rates) / len(tier1_staffed_late_rates)
    top_three = sorted(tier1_staffed_late_rates, key=lambda x: x[5], reverse=True)[:3]
    print("\nTier 1 average staffed-late breach rate (agents with >=20 tickets): {0:.2f}%".format(avg_rate))
    print("Top three agents by staffed-late rate:")
    for agent_id, name, team, tickets, sl, rate in top_three:
        print("  {0} ({1}, {2}): {3:.2f}% ({4}/{5})".format(agent_id, name, team, rate, sl, tickets))
else:
    print("\nNo Tier 1 agents with >=20 tickets found.")

# ---------- Print breach cause totals by month (optional) ----------
month_counts = defaultdict(lambda: {'no_cover':0, 'staffed_late':0})
with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        created_str = row['created_at']
        first_str = row['first_response_at']
        channel = row['channel'].strip().lower()
        created_dt = parse_datetime(created_str)
        first_dt = parse_datetime(first_str)
        if created_dt is None:
            continue
        breach = False
        cause = None
        response_minutes = None
        if first_dt is not None:
            diff = first_dt - created_dt
            response_minutes = diff.total_seconds() / 60.0
            if response_minutes >= 0:
                target = CHANNEL_TARGETS.get(channel)
                if target is not None and response_minutes > target:
                    breach = True
                    required_team = FRONTLINE_TEAM_BY_CHANNEL.get(channel)
                    if required_team is not None:
                        if has_coverage(required_team, created_dt.date(), get_shift_from_time(created_str[11:16])):
                            cause = 'staffed_late'
                        else:
                            cause = 'no_cover'
                    else:
                        cause = 'staffed_late'
        if breach:
            month_key = created_dt.strftime('%Y-%m')
            if cause == 'no_cover':
                month_counts[month_key]['no_cover'] += 1
            elif cause == 'staffed_late':
                month_counts[month_key]['staffed_late'] += 1

print("\nBreach cause totals by month:")
print("Month\tNo-Cover\tStaffed-Late")
for month in sorted(month_counts.keys()):
    nc = month_counts[month]['no_cover']
    sl = month_counts[month]['staffed_late']
    print("{0}\t{1}\t{2}".format(month, nc, sl))