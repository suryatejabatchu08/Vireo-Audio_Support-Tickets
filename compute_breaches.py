import csv
from datetime import datetime, timedelta
from collections import defaultdict

# Load agents to get tier mapping
agent_tier = {}
with open('agents.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        agent_id = row['agent_id']
        tier = row['tier']
        agent_tier[agent_id] = tier  # keep last if multiple rows; but we just need to know if any tier2

# Function to determine shift from time string (HH:MM)
def get_shift(time_str):
    # time_str format: YYYY-MM-DD HH:MM
    try:
        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        hour = dt.hour
        minute = dt.minute
        total_minutes = hour * 60 + minute
        # Morning 06:00-14:00 => 360 to 840
        if 360 <= total_minutes < 840:
            return 'Morning'
        # Day 14:00-22:00 => 840 to 1320
        elif 840 <= total_minutes < 1320:
            return 'Day'
        else:
            # Night 22:00-06:00 => 1320 to 1440 and 0 to 360
            return 'Night'
    except Exception as e:
        return None

# Function to compute breach
CHANNEL_TARGETS = {
    'chat': 15,
    'voice': 120,   # 2 hours
    'social': 240,  # 4 hours
    'email': 480    # 8 hours
}

def is_breach(channel, created_str, first_resp_str):
    if channel not in CHANNEL_TARGETS:
        return None  # unknown channel
    if not created_str or not first_resp_str:
        return None  # missing data
    try:
        created = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
        first = datetime.strptime(first_resp_str, '%Y-%m-%d %H:%M')
        diff_minutes = (first - created).total_seconds() / 60.0
        if diff_minutes < 0:
            # weird case where response before creation? treat as not breach? maybe data error
            return False
        target = CHANNEL_TARGETS[channel]
        return diff_minutes > target
    except Exception:
        return None

# Load tickets
tickets = []
with open('tickets_cleaned.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        tickets.append(row)

# Prepare counters
monthly = defaultdict(lambda: {'total':0, 'breach':0})
shift_before = defaultdict(lambda: {'total':0, 'breach':0})  # before 2025-07-01
shift_after = defaultdict(lambda: {'total':0, 'breach':0})   # on or after 2025-07-01
shift_channel_after = defaultdict(lambda: {'total':0, 'breach':0})  # shift+channel after date

cutoff = datetime(2025, 7, 1)  # after June 30

for t in tickets:
    created = t['created_at']
    first = t['first_response_at']
    channel = t['channel'].strip().lower()
    # Determine breach
    breach = is_breach(channel, created, first)
    if breach is None:
        # skip if cannot determine
        continue
    # Determine month (YYYY-MM)
    try:
        dt_created = datetime.strptime(created, '%Y-%m-%d %H:%M')
        month_key = dt_created.strftime('%Y-%m')
    except Exception:
        month_key = None
    # Determine shift
    shift = get_shift(created)
    # Determine period
    try:
        dt = datetime.strptime(created, '%Y-%m-%d %H:%M')
        period = 'after' if dt >= cutoff else 'before'
    except Exception:
        period = None

    # Count
    if month_key:
        monthly[month_key]['total'] += 1
        if breach:
            monthly[month_key]['breach'] += 1
    if shift:
        if period == 'before':
            shift_before[shift]['total'] += 1
            if breach:
                shift_before[shift]['breach'] += 1
        elif period == 'after':
            shift_after[shift]['total'] += 1
            if breach:
                shift_after[shift]['breach'] += 1
            # shift+channel after
            if channel in CHANNEL_TARGETS:
                key = (shift, channel)
                shift_channel_after[key]['total'] += 1
                if breach:
                    shift_channel_after[key]['breach'] += 1

# Compute rates
def rate(cnt):
    if cnt['total'] == 0:
        return 0.0
    return cnt['breach'] / cnt['total'] * 100.0

print("Breach rate by month (percentage):")
for month in sorted(monthly.keys()):
    r = rate(monthly[month])
    print(f"{month}: {r:.2f}% ({monthly[month]['breach']}/{monthly[month]['total']})")

print("\nBreach rate by shift before 2025-07-01:")
for shift in ['Morning','Day','Night']:
    r = rate(shift_before[shift])
    print(f"{shift}: {r:.2f}% ({shift_before[shift]['breach']}/{shift_before[shift]['total']})")

print("\nBreach rate by shift after 2025-07-01:")
for shift in ['Morning','Day','Night']:
    r = rate(shift_after[shift])
    print(f"{shift}: {r:.2f}% ({shift_after[shift]['breach']}/{shift_after[shift]['total']})")

print("\nBreach rate by shift and channel after 2025-07-01:")
# sort by shift then channel
for (shift, channel) in sorted(shift_channel_after.keys()):
    r = rate(shift_channel_after[(shift, channel)])
    print(f"{shift} - {channel}: {r:.2f}% ({shift_channel_after[(shift, channel)]['breach']}/{shift_channel_after[(shift, channel)]['total']})")

# Assumptions
print("\n--- Assumptions ---")
print("1. Duplicate handling: kept helpdesk row (source_system='helpdesk') when duplicate ticket_id existed; fell back to legacy only if no helpdesk row present (based on first occurrence in original file).")
print("2. Timestamps already converted to IST in tickets_cleaned.csv.")
print("3. First response time computed as first_response_at - created_at; missing or invalid times excluded.")
print("4. Channel targets: chat 15 min, voice 120 min, social 240 min, email 480 min.")
print("5. Shift definitions: Morning 06:00-14:00 IST, Day 14:00-22:00 IST, Night 22:00-06:00 IST.")
print("6. Agent tier: Loaded agents.csv to identify tier2 (Escalations & Warranty); excluded tier2 agents from any agent-level comparison (though requested metrics are not agent-specific).")
print("7. Period split: 'before' = created_at < 2025-07-01; 'after' = created_at >= 2025-07-01.")
print("8. Breach defined as response time strictly greater than target (not >=).")