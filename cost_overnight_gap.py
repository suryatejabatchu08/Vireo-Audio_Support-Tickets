import csv
from datetime import datetime, timedelta
from collections import defaultdict

# ---------- Configuration ----------
TICKETS_FILE = 'tickets_cleaned.csv'
AGENTS_FILE = 'agents.csv'

# Period: from 30 June 2025 (inclusive) to 30 June 2026 (inclusive?)
# We'll treat as [start_date, end_date) where end_date = 2026-07-01
START_DATE = datetime(2025, 6, 30)
END_DATE = datetime(2026, 7, 1)  # exclusive

CREDIT_AMOUNT = 350  # Rs per breach
AGENT_COST_PER_HOUR = 165  # Rs
SHIFT_HOURS = 8  # hours per shift

CHANNEL_TARGETS = {
    'chat': 15,        # minutes
    'voice': 120,      # 2 hours
    'social': 240,     # 4 hours
    'email': 480       # 8 hours
}

# Frontline teams per channel
FRONTLINE_TEAM_BY_CHANNEL = {
    'chat': 'Chat Frontline',
    'social': 'Chat Frontline',
    'email': 'Email Frontline',
    'voice': 'Voice Frontline'
}
FRONTLINE_TEAMS = set(FRONTLINE_TEAM_BY_CHANNEL.values())

# Shift definitions in minutes from 00:00
SHIFT_MINUTES = {
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

def is_resolved_or_closed(status):
    return status.strip().lower() in ('resolved', 'closed')

def is_open_or_pending(status):
    return status.strip().lower() in ('open', 'pending')

# ---------- Load agents ----------
agents_rows = []  # list of dicts
with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        agents_rows.append(row)

for r in agents_rows:
    r['from_date'] = datetime.strptime(r['from_date'], '%Y-%m-%d').date() if r['from_date'] else None
    r['to_date'] = datetime.strptime(r['to_date'], '%Y-%m-%d').date() if r['to_date'] else None

# Build mapping: agent_id -> list of assignments
agents_by_id = defaultdict(list)
for r in agents_rows:
    agents_by_id[r['agent_id']].append(r)
# Sort each list by from_date descending (most recent first)
for aid in agents_by_id:
    agents_by_id[aid].sort(key=lambda x: x['from_date'] or datetime.min.date(), reverse=True)

def get_agent_assignments_on_date(agent_id, target_date):
    """Return list of assignment dicts for agent_id valid on target_date."""
    res = []
    for a in agents_by_id.get(agent_id, []):
        if a['from_date'] and (a['to_date'] is None or target_date <= a['to_date']):
            if target_date >= a['from_date']:
                res.append(a)
    return res

def has_agent_on_date(team, shift, target_date):
    """Return True if there exists at least one agent with given team and shift valid on target_date."""
    for r in agents_rows:
        if r['team'] == team and r['shift'] == shift:
            if r['from_date'] and (r['to_date'] is None or target_date <= r['to_date']):
                if target_date >= r['from_date']:
                    return True
    return False

# ---------- Process tickets ----------
# Counters
total_tickets_resolved_closed = 0
open_pending_excluded = 0

night_tickets = 0
night_breaches = 0
night_no_cover_breaches = 0

morning_day_tickets = 0
morning_day_breaches = 0

# For storing night 'no cover' breach tickets for targeted cover analysis
night_no_cover_breach_details = []  # list of (created_dt, channel)
# For storing hours of all night tickets (for hourly distribution)
night_ticket_hours = []  # list of hours (0-23) for all night shift tickets
# For storing all night tickets details (for window analysis)
night_ticket_details = []  # list of (created_dt, channel)

# For roster coverage analysis
night_dates_with_coverage = set()  # dates where at least one frontline night agent is rostered

with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticket_id = row['ticket_id']
        created_str = row['created_at']
        first_str = row['first_response_at']
        status = row['status']
        channel = row['channel'].strip().lower()
        agent_id = row['agent_id']

        created_dt = parse_datetime(created_str)
        first_dt = parse_datetime(first_str)
        if created_dt is None:
            continue

        # Period filter
        if not (START_DATE <= created_dt < END_DATE):
            continue

        created_date = created_dt.date()
        shift = get_shift_from_time(created_str[11:16])
        if shift is None:
            continue

        # Determine if resolved/closed
        if is_resolved_or_closed(status):
            total_tickets_resolved_closed += 1
        elif is_open_or_pending(status):
            open_pending_excluded += 1
            # Still count for night/morning_day? Probably not for breach analysis.
            # We'll skip breach counting for open/pending as credit only on resolution.
            continue
        else:
            # Other status? treat as not resolved/closed for credit purposes.
            continue

        # Determine breach and cause
        breach = False
        cause = None  # 'no_cover' or 'staffed_late'
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
                        if has_agent_on_date(required_team, shift, created_date):
                            cause = 'staffed_late'
                        else:
                            cause = 'no_cover'
                    else:
                        # unknown channel, treat as staffed but late (should not happen)
                        cause = 'staffed_late'

        # Update counters
        if shift == 'Night':
            night_tickets += 1
            night_ticket_hours.append(created_dt.hour)  # for hourly distribution
            night_ticket_details.append((created_dt, channel))
            if breach:
                night_breaches += 1
                if cause == 'no_cover':
                    night_no_cover_breaches += 1
                    night_no_cover_breach_details.append((created_dt, channel))
        else:  # Morning or Day
            morning_day_tickets += 1
            if breach:
                morning_day_breaches += 1

        # Track dates with night coverage (for roster analysis)
        if shift == 'Night':
            # Check if any frontline night agent is rostered on this date
            if has_agent_on_date('Chat Frontline', 'Night', created_date) or \
               has_agent_on_date('Email Frontline', 'Night', created_date) or \
               has_agent_on_date('Voice Frontline', 'Night', created_date):
                night_dates_with_coverage.add(created_date)

# ---------- Calculations ----------
# Credit cost: count 'no cover' breaches (only resolved/closed) * 350
credit_cost_total = night_no_cover_breaches * CREDIT_AMOUNT
credit_cost_per_year = credit_cost_total  # period is 12 months
credit_cost_per_quarter = credit_cost_total / 4.0

# Unavoidable baseline: breach rate of Morning+Day tickets
if morning_day_tickets > 0:
    baseline_breach_rate = morning_day_breaches / morning_day_tickets
else:
    baseline_breach_rate = 0.0

# Expected breaches for Night tickets if they had same rate
expected_night_breaches = night_tickets * baseline_breach_rate
avoidable_breaches = night_breaches - expected_night_breaches
if avoidable_breaches < 0:
    avoidable_breaches = 0
avoidable_credit_cost_total = avoidable_breaches * CREDIT_AMOUNT
avoidable_credit_cost_per_year = avoidable_credit_cost_total
avoidable_credit_cost_per_quarter = avoidable_credit_cost_total / 4.0

# Cost of the fix (full-shift reference)
cost_per_agent_per_night_shift = AGENT_COST_PER_HOUR * SHIFT_HOURS  # Rs
cost_per_agent_per_day = cost_per_agent_per_night_shift  # one shift per day
# Number of days in period
days_in_period = (END_DATE - START_DATE).days
nights_per_year = days_in_period  # one night per day
nights_per_quarter = nights_per_year / 4.0
cost_per_agent_per_year = cost_per_agent_per_night_shift * nights_per_year
cost_per_agent_per_quarter = cost_per_agent_per_night_shift * nights_per_quarter

# Night agents before and after
# Before: valid on 2025-06-29 (day before start)
BEFORE_DATE = datetime(2025, 6, 29).date()
night_agents_before_set = set()
for agent_id, assignments in agents_by_id.items():
    for a in assignments:
        if a['team'] in FRONTLINE_TEAMS and a['shift'] == 'Night':
            if a['from_date'] and (a['to_date'] is None or BEFORE_DATE <= a['to_date']):
                if BEFORE_DATE >= a['from_date']:
                    night_agents_before_set.add(agent_id)
                    break  # count agent once
night_agents_before = len(night_agents_before_set)

# After: valid on 2026-06-30 (last date in period)
AFTER_DATE = datetime(2026, 6, 30).date()
night_agents_after_set = set()
for agent_id, assignments in agents_by_id.items():
    for a in assignments:
        if a['team'] in FRONTLINE_TEAMS and a['shift'] == 'Night':
            if a['from_date'] and (a['to_date'] is None or AFTER_DATE <= a['to_date']):
                if AFTER_DATE >= a['from_date']:
                    night_agents_after_set.add(agent_id)
                    break
night_agents_after = len(night_agents_after_set)

# Roster coverage: proportion of nights with at least one frontline night agent
# We consider all nights in the period (each date has one night shift ending on that date)
period_start_date = START_DATE.date()
period_end_date = END_DATE.date() - timedelta(days=1)  # inclusive end
total_nights_in_period = 0
nights_with_coverage = 0
current_date = period_start_date
while current_date <= period_end_date:
    total_nights_in_period += 1
    if has_agent_on_date('Chat Frontline', 'Night', current_date) or \
       has_agent_on_date('Email Frontline', 'Night', current_date) or \
       has_agent_on_date('Voice Frontline', 'Night', current_date):
        nights_with_coverage += 1
    current_date += timedelta(days=1)

coverage_proportion = nights_with_coverage / total_nights_in_period if total_nights_in_period > 0 else 0.0

# Minimal rota needed to cover overnight volume
# We'll compute average overnight ticket volume per hour
total_night_hours = nights_per_year * SHIFT_HOURS  # 8 hours per night
if total_night_hours > 0:
    avg_overnight_tickets_per_hour = night_tickets / total_night_hours
else:
    avg_overnight_tickets_per_hour = 0.0

# Targeted cover options analysis
# We have night_no_cover_breach_details: list of (created_dt, channel) for each night 'no cover' breach
# We also have night_ticket_details: list of (created_dt, channel) for all night tickets
from datetime import time

def in_window_22_02(dt):
    """Check if time is between 22:00 and 02:00 (crosses midnight)."""
    t = dt.time()
    return t >= time(22, 0) or t < time(2, 0)

def in_window_22_04(dt):
    """Check if time is between 22:00 and 04:00 (crosses midnight)."""
    t = dt.time()
    return t >= time(22, 0) or t < time(4, 0)

def in_window_chat_whole_night(dt, channel):
    """Check if channel is chat and time is between 22:00 and 06:00 (crosses midnight)."""
    if channel != 'chat':
        return False
    t = dt.time()
    return t >= time(22, 0) or t < time(6, 0)

def in_window_chat_social_22_04(dt, channel):
    """Check if channel is chat or social and time is between 22:00 and 04:00 (crosses midnight)."""
    if channel not in ('chat', 'social'):
        return False
    t = dt.time()
    return t >= time(22, 0) or t < time(4, 0)

# For each option, compute:
#   tickets_in_window: count of night tickets in the window (and channel if applicable)
#   breaches_in_window: count of night 'no cover' breaches in the window (and channel if applicable)
#   expected_breaches_in_window = baseline_breach_rate * tickets_in_window
#   avoided_breaches = max(0, breaches_in_window - expected_breaches_in_window)

# Option 1: 22:00 to 02:00
tickets_22_02 = 0
breaches_22_02 = 0
for dt, channel in night_ticket_details:
    if in_window_22_02(dt):
        tickets_22_02 += 1
for dt, channel in night_no_cover_breach_details:
    if in_window_22_02(dt):
        breaches_22_02 += 1
expected_22_02 = baseline_breach_rate * tickets_22_02
avoidable_22_02 = max(0, breaches_22_02 - expected_22_02)

# Option 2: 22:00 to 04:00
tickets_22_04 = 0
breaches_22_04 = 0
for dt, channel in night_ticket_details:
    if in_window_22_04(dt):
        tickets_22_04 += 1
for dt, channel in night_no_cover_breach_details:
    if in_window_22_04(dt):
        breaches_22_04 += 1
expected_22_04 = baseline_breach_rate * tickets_22_04
avoidable_22_04 = max(0, breaches_22_04 - expected_22_04)

# Option 3: chat only for whole night (22:00-06:00)
tickets_chat_whole = 0
breaches_chat_whole = 0
for dt, channel in night_ticket_details:
    if in_window_chat_whole_night(dt, channel):
        tickets_chat_whole += 1
for dt, channel in night_no_cover_breach_details:
    if in_window_chat_whole_night(dt, channel):
        breaches_chat_whole += 1
expected_chat_whole = baseline_breach_rate * tickets_chat_whole
avoidable_chat_whole = max(0, breaches_chat_whole - expected_chat_whole)

# Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00
tickets_chat_social_22_04 = 0
breaches_chat_social_22_04 = 0
for dt, channel in night_ticket_details:
    if in_window_chat_social_22_04(dt, channel):
        tickets_chat_social_22_04 += 1
for dt, channel in night_no_cover_breach_details:
    if in_window_chat_social_22_04(dt, channel):
        breaches_chat_social_22_04 += 1
expected_chat_social_22_04 = baseline_breach_rate * tickets_chat_social_22_04
avoidable_chat_social_22_04 = max(0, breaches_chat_social_22_04 - expected_chat_social_22_04)

# Compute avoided credit cost per quarter for each option
credit_per_breach = CREDIT_AMOUNT
avoidable_credit_22_02_total = avoidable_22_02 * credit_per_breach
avoidable_credit_22_02_per_quarter = avoidable_credit_22_02_total / 4.0
avoidable_credit_22_04_total = avoidable_22_04 * credit_per_breach
avoidable_credit_22_04_per_quarter = avoidable_credit_22_04_total / 4.0
avoidable_credit_chat_whole_total = avoidable_chat_whole * credit_per_breach
avoidable_credit_chat_whole_per_quarter = avoidable_credit_chat_whole_total / 4.0
avoidable_credit_chat_social_22_04_total = avoidable_chat_social_22_04 * credit_per_breach
avoidable_credit_chat_social_22_04_per_quarter = avoidable_credit_chat_social_22_04_total / 4.0

# Hourly distribution of overnight tickets (all night shift tickets) - only night hours 22-05
hourly_counts = [0] * 24
for hour in night_ticket_hours:
    if 0 <= hour < 24:
        hourly_counts[hour] += 1
# We'll only show hours 22,23,0,1,2,3,4,5
night_hours = list(range(22, 24)) + list(range(0, 6))
hourly_shares = {}
for hour in night_hours:
    count = hourly_counts[hour]
    share = (count / len(night_ticket_hours) * 100) if len(night_ticket_hours) > 0 else 0.0
    hourly_shares[hour] = (share, count)

# ---------- Output ----------
print("=== Assumptions ===")
print(f"1. Period: {START_DATE.date()} to {END_DATE.date()-timedelta(days=1)} (inclusive).")
print("2. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.")
print("3. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).")
print("4. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.")
print("5. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).")
print("6. Morning and Day breach rate used as unavoidable baseline for Night tickets.")
print("7. Credit issued per breach regardless of cause, amount Rs 350.")
print("8. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs {0} per night shift per agent.".format(cost_per_agent_per_night_shift))
print("9. Number of nights in period = {0} (one per day).".format(nights_per_year))
print("10. Headcount is frozen; we can only reassign existing agents, not hire new.")
print("11. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).")
print()

print("=== Credit Cost ===")
print(f"Night 'no cover' breaches (resolved/closed) in period: {night_no_cover_breaches}")
print(f"Open or pending tickets excluded (status open/pending): {open_pending_excluded}")
print(f"Credit cost per breach: Rs {CREDIT_AMOUNT}")
print(f"Total credit cost (no cover breaches): Rs {credit_cost_total:,.0f}")
print(f"Credit cost per year: Rs {credit_cost_per_year:,.0f}")
print(f"Credit cost per quarter: Rs {credit_cost_per_quarter:,.0f}")
print()

print("=== Unavoidable Baseline ===")
print(f"Morning+Day tickets (resolved/closed): {morning_day_tickets}")
print(f"Morning+Day breaches: {morning_day_breaches}")
if morning_day_tickets > 0:
    print(f"Baseline breach rate (Morning+Day): {baseline_breach_rate:.4f} ({baseline_breach_rate*100:.2f}%)")
else:
    print("Baseline breach rate: N/A (no Morning+Day tickets)")
print(f"Expected Night breaches if same rate: {expected_night_breaches:.2f}")
print(f"Actual Night breaches: {night_breaches}")
print(f"Avoidable breaches (actual - expected): {avoidable_breaches:.2f} => {int(round(avoidable_breaches))}")
print(f"Avoidable credit cost per year: Rs {avoidable_credit_cost_per_year:,.0f}")
print(f"Avoidable credit cost per quarter: Rs {avoidable_credit_cost_per_quarter:,.0f}")
print()

print("=== Full-Shift Cost Reference (for 8-hour night shift) ===")
print(f"Cost per agent per night shift: Rs {cost_per_agent_per_night_shift:,.0f}")
print(f"Cost per agent per day: Rs {cost_per_agent_per_day:,.0f}")
print(f"Cost per agent per year: Rs {cost_per_agent_per_year:,.0f}")
print(f"Cost per agent per quarter: Rs {cost_per_agent_per_quarter:,.0f}")
print()

print(f"Night agents (Chat Frontline, Email Frontline, Voice Frontline) on roster before {BEFORE_DATE}: {night_agents_before}")
print(f"Night agents (same teams) on roster after {AFTER_DATE}: {night_agents_after}")
print()

print(f"Total nights in period: {total_nights_in_period}")
print(f"Nights with at least one frontline night agent rostered: {nights_with_coverage}")
print(f"Coverage proportion: {coverage_proportion:.2%}")
print()

print(f"Average overnight ticket volume per hour: {avg_overnight_tickets_per_hour:.3f} tickets/hour")
print(f"(Total night tickets: {night_tickets}, total night hours: {total_night_hours:.0f})")
print()

print("=== Targeted Cover Options Analysis ===")
print(f"Night 'no cover' breaches (resolved/closed) in period: {night_no_cover_breaches}")
print()
print("Option 1: Agent covers 22:00 to 02:00")
print(f"  Tickets in window: {tickets_22_02}")
print(f"  Actual breaches in window: {breaches_22_02}")
print(f"  Expected breaches in window: {expected_22_02:.2f}")
print(f"  Breaches avoided: {avoidable_22_02:.2f} => {int(round(avoidable_22_02))}")
print(f"  Credit saved per year: Rs {avoidable_credit_22_02_total:,.0f}")
print(f"  Credit saved per quarter: Rs {avoidable_credit_22_02_per_quarter:,.0f}")
print()
print("Option 2: Agent covers 22:00 to 04:00")
print(f"  Tickets in window: {tickets_22_04}")
print(f"  Actual breaches in window: {breaches_22_04}")
print(f"  Expected breaches in window: {expected_22_04:.2f}")
print(f"  Breaches avoided: {avoidable_22_04:.2f} => {int(round(avoidable_22_04))}")
print(f"  Credit saved per year: Rs {avoidable_credit_22_04_total:,.0f}")
print(f"  Credit saved per quarter: Rs {avoidable_credit_22_04_per_quarter:,.0f}")
print()
print("Option 3: Agent covers chat only for whole night (22:00-06:00)")
print(f"  Tickets in window: {tickets_chat_whole}")
print(f"  Actual breaches in window: {breaches_chat_whole}")
print(f"  Expected breaches in window: {expected_chat_whole:.2f}")
print(f"  Breaches avoided: {avoidable_chat_whole:.2f} => {int(round(avoidable_chat_whole))}")
print(f"  Credit saved per year: Rs {avoidable_credit_chat_whole_total:,.0f}")
print(f"  Credit saved per quarter: Rs {avoidable_credit_chat_whole_per_quarter:,.0f}")
print()
print("Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00")
print(f"  Tickets in window: {tickets_chat_social_22_04}")
print(f"  Actual breaches in window: {breaches_chat_social_22_04}")
print(f"  Expected breaches in window: {expected_chat_social_22_04:.2f}")
print(f"  Breaches avoided: {avoidable_chat_social_22_04:.2f} => {int(round(avoidable_chat_social_22_04))}")
print(f"  Credit saved per year: Rs {avoidable_credit_chat_social_22_04_total:,.0f}")
print(f"  Credit saved per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f}")
print()
print("Hourly share of overnight tickets (night hours only):")
for hour in night_hours:
    share, count = hourly_shares[hour]
    print(f"  {hour:02d}:00 - {hour:02d}:59: {share:.2f}% ({count} tickets)")
print()

# Compute overall breach rate after each option
total_breaches = night_breaches + morning_day_breaches
total_tickets = total_tickets_resolved_closed
overall_breach_rate_before = total_breaches / total_tickets if total_tickets > 0 else 0.0

# For each option, compute overall breach rate after applying that option's avoided breaches
def overall_breach_rate_after(avoidable_breaches_option):
    breaches_after = total_breaches - avoidable_breaches_option
    return breaches_after / total_tickets if total_tickets > 0 else 0.0

rate_after_22_02 = overall_breach_rate_after(avoidable_22_02)
rate_after_22_04 = overall_breach_rate_after(avoidable_22_04)
rate_after_chat_whole = overall_breach_rate_after(avoidable_chat_whole)
rate_after_chat_social_22_04 = overall_breach_rate_after(avoidable_chat_social_22_04)

# Determine best option (lowest overall breach rate after)
options = [
    ("22:00-02:00", avoidable_22_02, rate_after_22_02),
    ("22:00-04:00", avoidable_22_04, rate_after_22_04),
    ("chat only 22:00-06:00", avoidable_chat_whole, rate_after_chat_whole),
    ("chat+social 22:00-04:00", avoidable_chat_social_22_04, rate_after_chat_social_22_04)
]
best_option = min(options, key=lambda x: x[2])  # lowest breach rate
best_option_name, best_avoidable, best_rate_after = best_option

print("=== Net Impact ===")
# Scenario 1: New hire - compute cost per quarter for each option based on hours covered
def cost_per_quarter_for_hours(hours_per_night):
    # cost per night = hours_per_night * AGENT_COST_PER_HOUR
    # cost per year = cost per night * nights_per_year
    # cost per quarter = cost per year / 4
    return (hours_per_night * AGENT_COST_PER_HOUR * nights_per_year) / 4.0

# Hours per night for each option
hours_22_02 = 4.0   # 22:00 to 02:00 is 4 hours
hours_22_04 = 6.0   # 22:00 to 04:00 is 6 hours
hours_chat_whole = 8.0  # 22:00 to 06:00 is 8 hours
hours_chat_social_22_04 = 6.0  # same as option 2

cost_22_02 = cost_per_quarter_for_hours(hours_22_02)
cost_22_04 = cost_per_quarter_for_hours(hours_22_04)
cost_chat_whole = cost_per_quarter_for_hours(hours_chat_whole)
cost_chat_social_22_04 = cost_per_quarter_for_hours(hours_chat_social_22_04)

print("If a new agent is hired for night shift:")
print(f"  Option 1 (22:00-02:00, {hours_22_02}h):")
print(f"    Extra cost per quarter: Rs {cost_22_02:,.0f}")
print(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_22_02_per_quarter:,.0f}")
print(f"    Net saving per quarter: Rs {avoidable_credit_22_02_per_quarter - cost_22_02:,.0f}")
print()
print(f"  Option 2 (22:00-04:00, {hours_22_04}h):")
print(f"    Extra cost per quarter: Rs {cost_22_04:,.0f}")
print(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_22_04_per_quarter:,.0f}")
print(f"    Net saving per quarter: Rs {avoidable_credit_22_04_per_quarter - cost_22_04:,.0f}")
print()
print(f"  Option 3 (chat only 22:00-06:00, {hours_chat_whole}h):")
print(f"    Extra cost per quarter: Rs {cost_chat_whole:,.0f}")
print(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_chat_whole_per_quarter:,.0f}")
print(f"    Net saving per quarter: Rs {avoidable_credit_chat_whole_per_quarter - cost_chat_whole:,.0f}")
print()
print(f"  Option 4 (chat+social 22:00-04:00, {hours_chat_social_22_04}h):")
print(f"    Extra cost per quarter: Rs {cost_chat_social_22_04:,.0f}")
print(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f}")
print(f"    Net saving per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter - cost_chat_social_22_04:,.0f}")
print()

# Scenario 2: Reassignment of existing agent (no salary change)
print("If an existing agent is reassigned from day/morning to night shift (no salary change):")
print(f"  Extra cost per quarter: Rs 0 (same agent)")
print(f"  Avoidable credit saving per quarter (Option 1): Rs {avoidable_credit_22_02_per_quarter:,.0f}")
print(f"  Net saving per quarter: Rs {avoidable_credit_22_02_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
print(f"  Avoidable credit saving per quarter (Option 2): Rs {avoidable_credit_22_04_per_quarter:,.0f}")
print(f"  Net saving per quarter: Rs {avoidable_credit_22_04_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
print(f"  Avoidable credit saving per quarter (Option 3): Rs {avoidable_credit_chat_whole_per_quarter:,.0f}")
print(f"  Net saving per quarter: Rs {avoidable_credit_chat_whole_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
print(f"  Avoidable credit saving per quarter (Option 4): Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f}")
print(f"  Net saving per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
print(f"  Impact: One fewer frontline agent available for day/morning shifts.")
print()

print("=== Overall Breach Rate ===")
print(f"Total tickets (resolved/closed) in period: {total_tickets}")
print(f"Total breaches (Night + Morning+Day): {total_breaches}")
print(f"Overall breach rate before fixing gap: {overall_breach_rate_before:.4f} ({overall_breach_rate_before*100:.2f}%)")
print(f"Overall breach rate after eliminating avoidable breaches (baseline): {(total_breaches - avoidable_breaches) / total_tickets:.4f} ({(total_breaches - avoidable_breaches) / total_tickets * 100:.2f}%)")
print(f"Overall breach rate after Option 1 (22:00-02:00): {rate_after_22_02:.4f} ({rate_after_22_02*100:.2f}%)")
print(f"Overall breach rate after Option 2 (22:00-04:00): {rate_after_22_04:.4f} ({rate_after_22_04*100:.2f}%)")
print(f"Overall breach rate after Option 3 (chat only 22:00-06:00): {rate_after_chat_whole:.4f} ({rate_after_chat_whole*100:.2f}%)")
print(f"Overall breach rate after Option 4 (chat+social 22:00-04:00): {rate_after_chat_social_22_04:.4f} ({rate_after_chat_social_22_04*100:.2f}%)")
print(f"Reduction in overall breach rate (baseline): {avoidable_breaches / total_tickets:.4f} ({avoidable_breaches / total_tickets * 100:.2f} percentage points)")
print(f"Reduction in overall breach rate (Option 1): {(overall_breach_rate_before - rate_after_22_02):.4f} ({(overall_breach_rate_before - rate_after_22_02)*100:.2f} percentage points)")
print(f"Reduction in overall breach rate (Option 2): {(overall_breach_rate_before - rate_after_22_04):.4f} ({(overall_breach_rate_before - rate_after_22_04)*100:.2f} percentage points)")
print(f"Reduction in overall breach rate (Option 3): {(overall_breach_rate_before - rate_after_chat_whole):.4f} ({(overall_breach_rate_before - rate_after_chat_whole)*100:.2f} percentage points)")
print(f"Reduction in overall breach rate (Option 4): {(overall_breach_rate_before - rate_after_chat_social_22_04):.4f} ({(overall_breach_rate_before - rate_after_chat_social_22_04)*100:.2f} percentage points)")
print()

print("=== Headline Goal ===")
# Use Option 1 for headline goal
print(f"Cut the overall breach rate from about {overall_breach_rate_before*100:.0f}% to about {rate_after_22_02*100:.0f}%, worth roughly Rs {avoidable_credit_22_02_per_quarter:,.0f} a quarter.")
print()

# ---------- Log to LOG.md ----------
log_entries = []
log_entries.append("### Cost of Overnight Coverage Gap Analysis")
log_entries.append(f"**Period**: {START_DATE.date()} to {END_DATE.date()-timedelta(days=1)}")
log_entries.append("**Assumptions**:")
log_entries.append("1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.")
log_entries.append("2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).")
log_entries.append("3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.")
log_entries.append("4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).")
log_entries.append("5. Morning and Day breach rate used as unavoidable baseline for Night tickets.")
log_entries.append("6. Credit issued per breach regardless of cause, amount Rs 350.")
log_entries.append("7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs {0} per night shift per agent.".format(cost_per_agent_per_night_shift))
log_entries.append("8. Number of nights in period = {0} (one per day).".format(nights_per_year))
log_entries.append("9. Headcount is frozen; we can only reassign existing agents, not hire new.")
log_entries.append("10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).")
log_entries.append("")
log_entries.append("**Results**:")
log_entries.append(f"- Night 'no cover' breaches (resolved/closed): {night_no_cover_breaches}")
log_entries.append(f"- Open or pending tickets excluded: {open_pending_excluded}")
log_entries.append(f"- Credit cost per breach: Rs {CREDIT_AMOUNT}")
log_entries.append(f"- Total credit cost (no cover breaches): Rs {credit_cost_total:,.0f}")
log_entries.append(f"- Credit cost per year: Rs {credit_cost_per_year:,.0f}")
log_entries.append(f"- Credit cost per quarter: Rs {credit_cost_per_quarter:,.0f}")
log_entries.append("")
log_entries.append(f"- Morning+Day tickets: {morning_day_tickets}")
log_entries.append(f"- Morning+Day breaches: {morning_day_breaches}")
log_entries.append(f"- Baseline breach rate (Morning+Day): {baseline_breach_rate*100:.2f}%")
log_entries.append(f"- Expected Night breaches if same rate: {expected_night_breaches:.2f}")
log_entries.append(f"- Actual Night breaches: {night_breaches}")
log_entries.append(f"- Avoidable breaches (actual - expected): {avoidable_breaches:.2f} => {int(round(avoidable_breaches))}")
log_entries.append(f"- Avoidable credit cost per year: Rs {avoidable_credit_cost_per_year:,.0f}")
log_entries.append(f"- Avoidable credit cost per quarter: Rs {avoidable_credit_cost_per_quarter:,.0f}")
log_entries.append("")
log_entries.append(f"- Cost per agent per night shift: Rs {cost_per_agent_per_night_shift:,.0f}")
log_entries.append(f"- Cost per agent per day: Rs {cost_per_agent_per_day:,.0f}")
log_entries.append(f"- Cost per agent per year: Rs {cost_per_agent_per_year:,.0f}")
log_entries.append(f"- Cost per agent per quarter: Rs {cost_per_agent_per_quarter:,.0f}")
log_entries.append("")
log_entries.append(f"- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before {BEFORE_DATE}: {night_agents_before}")
log_entries.append(f"- Night agents (same teams) after {AFTER_DATE}: {night_agents_after}")
log_entries.append("")
log_entries.append(f"- Total nights in period: {total_nights_in_period}")
log_entries.append(f"- Nights with at least one frontline night agent rostered: {nights_with_coverage}")
log_entries.append(f"- Coverage proportion: {coverage_proportion:.2%}")
log_entries.append("")
log_entries.append(f"- Average overnight ticket volume per hour: {avg_overnight_tickets_per_hour:.3f} tickets/hour")
log_entries.append(f"(Total night tickets: {night_tickets}, total night hours: {total_night_hours:.0f})")
log_entries.append("")
log_entries.append("**Targeted Cover Options Analysis**:")
log_entries.append(f"- Night 'no cover' breaches (resolved/closed) in period: {night_no_cover_breaches}")
log_entries.append("")
log_entries.append("Option 1: Agent covers 22:00 to 02:00")
log_entries.append(f"  Tickets in window: {tickets_22_02}")
log_entries.append(f"  Actual breaches in window: {breaches_22_02}")
log_entries.append(f"  Expected breaches in window: {expected_22_02:.2f}")
log_entries.append(f"  Breaches avoided: {avoidable_22_02:.2f} => {int(round(avoidable_22_02))}")
log_entries.append(f"  Credit saved per year: Rs {avoidable_credit_22_02_total:,.0f}")
log_entries.append(f"  Credit saved per quarter: Rs {avoidable_credit_22_02_per_quarter:,.0f}")
log_entries.append("")
log_entries.append("Option 2: Agent covers 22:00 to 04:00")
log_entries.append(f"  Tickets in window: {tickets_22_04}")
log_entries.append(f"  Actual breaches in window: {breaches_22_04}")
log_entries.append(f"  Expected breaches in window: {expected_22_04:.2f}")
log_entries.append(f"  Breaches avoided: {avoidable_22_04:.2f} => {int(round(avoidable_22_04))}")
log_entries.append(f"  Credit saved per year: Rs {avoidable_credit_22_04_total:,.0f}")
log_entries.append(f"  Credit saved per quarter: Rs {avoidable_credit_22_04_per_quarter:,.0f}")
log_entries.append("")
log_entries.append("Option 3: Agent covers chat only for whole night (22:00-06:00)")
log_entries.append(f"  Tickets in window: {tickets_chat_whole}")
log_entries.append(f"  Actual breaches in window: {breaches_chat_whole}")
log_entries.append(f"  Expected breaches in window: {expected_chat_whole:.2f}")
log_entries.append(f"  Breaches avoided: {avoidable_chat_whole:.2f} => {int(round(avoidable_chat_whole))}")
log_entries.append(f"  Credit saved per year: Rs {avoidable_credit_chat_whole_total:,.0f}")
log_entries.append(f"  Credit saved per quarter: Rs {avoidable_credit_chat_whole_per_quarter:,.0f}")
log_entries.append("")
log_entries.append("Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00")
log_entries.append(f"  Tickets in window: {tickets_chat_social_22_04}")
log_entries.append(f"  Actual breaches in window: {breaches_chat_social_22_04}")
log_entries.append(f"  Expected breaches in window: {expected_chat_social_22_04:.2f}")
log_entries.append(f"  Breaches avoided: {avoidable_chat_social_22_04:.2f} => {int(round(avoidable_chat_social_22_04))}")
log_entries.append(f"  Credit saved per year: Rs {avoidable_credit_chat_social_22_04_total:,.0f}")
log_entries.append(f"  Credit saved per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f}")
log_entries.append("")
log_entries.append("Hourly share of overnight tickets (night hours only):")
for hour in night_hours:
    share, count = hourly_shares[hour]
    log_entries.append(f"  {hour:02d}:00 - {hour:02d}:59: {share:.2f}% ({count} tickets)")
log_entries.append("")
log_entries.append("**Net Impact**:")
log_entries.append("- If a new agent is hired for night shift:")
log_entries.append(f"  Option 1 (22:00-02:00, {hours_22_02}h):")
log_entries.append(f"    Extra cost per quarter: Rs {cost_22_02:,.0f}")
log_entries.append(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_22_02_per_quarter:,.0f}")
log_entries.append(f"    Net saving per quarter: Rs {avoidable_credit_22_02_per_quarter - cost_22_02:,.0f}")
log_entries.append("")
log_entries.append(f"  Option 2 (22:00-04:00, {hours_22_04}h):")
log_entries.append(f"    Extra cost per quarter: Rs {cost_22_04:,.0f}")
log_entries.append(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_22_04_per_quarter:,.0f}")
log_entries.append(f"    Net saving per quarter: Rs {avoidable_credit_22_04_per_quarter - cost_22_04:,.0f}")
log_entries.append("")
log_entries.append(f"  Option 3 (chat only 22:00-06:00, {hours_chat_whole}h):")
log_entries.append(f"    Extra cost per quarter: Rs {cost_chat_whole:,.0f}")
log_entries.append(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_chat_whole_per_quarter:,.0f}")
log_entries.append(f"    Net saving per quarter: Rs {avoidable_credit_chat_whole_per_quarter - cost_chat_whole:,.0f}")
log_entries.append("")
log_entries.append(f"  Option 4 (chat+social 22:00-04:00, {hours_chat_social_22_04}h):")
log_entries.append(f"    Extra cost per quarter: Rs {cost_chat_social_22_04:,.0f}")
log_entries.append(f"    Avoidable credit saving per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f}")
log_entries.append(f"    Net saving per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter - cost_chat_social_22_04:,.0f}")
log_entries.append("")
log_entries.append("- If an existing agent is reassigned from day/morning to night shift (no salary change):")
log_entries.append(f"  Extra cost per quarter: Rs 0 (same agent)")
log_entries.append(f"  Avoidable credit saving per quarter (Option 1): Rs {avoidable_credit_22_02_per_quarter:,.0f}")
log_entries.append(f"  Net saving per quarter: Rs {avoidable_credit_22_02_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
log_entries.append(f"  Avoidable credit saving per quarter (Option 2): Rs {avoidable_credit_22_04_per_quarter:,.0f}")
log_entries.append(f"  Net saving per quarter: Rs {avoidable_credit_22_04_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
log_entries.append(f"  Avoidable credit saving per quarter (Option 3): Rs {avoidable_credit_chat_whole_per_quarter:,.0f}")
log_entries.append(f"  Net saving per quarter: Rs {avoidable_credit_chat_whole_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
log_entries.append(f"  Avoidable credit saving per quarter (Option 4): Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f}")
log_entries.append(f"  Net saving per quarter: Rs {avoidable_credit_chat_social_22_04_per_quarter:,.0f} (but lose one agent from day/morning shifts)")
log_entries.append(f"  Impact: One fewer frontline agent available for day/morning shifts.")
log_entries.append("")
log_entries.append(f"- Total tickets (resolved/closed) in period: {total_tickets}")
log_entries.append(f"- Total breaches (Night + Morning+Day): {total_breaches}")
log_entries.append(f"- Overall breach rate before fixing gap: {overall_breach_rate_before*100:.2f}%")
log_entries.append(f"- Overall breach rate after eliminating avoidable breaches (baseline): {(total_breaches - avoidable_breaches) / total_tickets * 100:.2f}%")
log_entries.append(f"- Overall breach rate after Option 1 (22:00-02:00): {rate_after_22_02*100:.2f}%")
log_entries.append(f"- Overall breach rate after Option 2 (22:00-04:00): {rate_after_22_04*100:.2f}%")
log_entries.append(f"- Overall breach rate after Option 3 (chat only 22:00-06:00): {rate_after_chat_whole*100:.2f}%")
log_entries.append(f"- Overall breach rate after Option 4 (chat+social 22:00-04:00): {rate_after_chat_social_22_04*100:.2f}%")
log_entries.append(f"- Reduction in overall breach rate (baseline): {avoidable_breaches / total_tickets * 100:.2f} percentage points")
log_entries.append(f"- Reduction in overall breach rate (Option 1): {(overall_breach_rate_before - rate_after_22_02)*100:.2f} percentage points")
log_entries.append(f"- Reduction in overall breach rate (Option 2): {(overall_breach_rate_before - rate_after_22_04)*100:.2f} percentage points")
log_entries.append(f"- Reduction in overall breach rate (Option 3): {(overall_breach_rate_before - rate_after_chat_whole)*100:.2f} percentage points")
log_entries.append(f"- Reduction in overall breach rate (Option 4): {(overall_breach_rate_before - rate_after_chat_social_22_04)*100:.2f} percentage points")
log_entries.append("")
log_entries.append("**Note**: Ticket volume doubled from July 2025 across all channels, driven by product VA-EB-PL2. This was not investigated further.")
log_entries.append("")
log_entries.append(f"### Headline Goal")
log_entries.append(f"Cut the overall breach rate from about {overall_breach_rate_before*100:.0f}% to about {rate_after_22_02*100:.0f}%, worth roughly Rs {avoidable_credit_22_02_per_quarter:,.0f} a quarter.")
log_entries.append("")

with open('LOG.md', 'a', encoding='utf-8') as logf:
    logf.write('\n'.join(log_entries) + '\n')

print("Logged assumptions and results to LOG.md")