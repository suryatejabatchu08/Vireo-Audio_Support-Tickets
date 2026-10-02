# LOG - Vireo Audio Support Tickets Analysis

## 2026-10-01

### Initial Analysis
- Read README.txt to understand data structure
- Attempted to read support-policy.pdf but encountered PDF rendering issues
- Read email-thread.txt for context about SLA breach reports
- Examined tickets.csv and agents.csv to understand data patterns

### Key Findings So Far
1. **Data Structure** (from README.txt):
   - tickets.csv: Support tickets with fields including timestamps, status, channel, priority, etc.
   - agents.csv: Roster with shift information (Day, Night, Morning shifts)
   - orders.csv, customers.csv, products.csv: Supporting data

2. **Email Thread Insights**:
   - SLA breach reports requested weekly by agent and shift
   - Timezone issue: Export data in UTC, but shift definitions in policy are IST
   - Data quality issues mentioned:
     - Some tickets appear twice from migration re-import
     - Legacy rows have csat 0 where new system leaves blank
     - About forty messages are failed IVR transcripts
   - Financial context: SLA credit line in P&L has tripled since last summer
   - Operational concern: Morning chat team demoralized by "wall of red" (SLA breach reports)

3. **Preliminary Data Examination**:
   - Agents.csv shows shift patterns: Day, Night, Morning
   - Ticket data shows varying response times (8 minutes to several hours)
   - CSAT scores: Many 0 (no response), some 4s and 5s
   - Refund amounts: Various INR values (2499, 3499, etc.)
   - Refund reason codes include RETURN-QC-OK, DUP-PAYMENT, CANCEL, etc.

### Information Extracted from support-policy.pdf

**SLA Targets (Section 3):**
- First response targets:
  - Chat: 15 minutes
  - Voice callback: 2 hours
  - Social: 4 hours
  - Email: 8 hours
- Breach penalty: Rs 350 store credit per ticket (charged to SLA credit line in P&L)

**Cost Figures (Section 4):**
- Fully loaded cost per contact:
  - Chat: Rs 210
  - Email: Rs 260
  - Voice callback: Rs 520
  - Social: Rs 240
  - Blended average: Rs 290 per contact
- Internal transfer cost: Rs 305 per transfer
- Fully loaded agent cost: Rs 165 per agent-hour
- Single agent shift: 8 hours

**Shift Definitions (Section 7):**
- Morning: 06:00-14:00 IST
- Day: 14:00-22:00 IST
- Night: 22:00-06:00 IST
- Roster: One row per assignment with from/to dates

**Data Traps (Sections 9 and email thread):**
1. Timezone mismatch: Helpdesk API exports UTC, but shift definitions and standard reports use IST
2. Legacy data duplication: Subset of legacy tickets re-imported during reconciliation may appear under both source systems (helpdesk and legacy_fd)
3. Legacy tool data incompatibility: Legacy tool stored monetary values in native unit; current helpdesk stores rupees
4. Resolution timestamp reconstruction: For migrated tickets, resolution timestamps were reconstructed from legacy event log (which stores UTC)
5. CSAT scoring inconsistency: Legacy rows use 0 for no response; new system leaves it blank
6. Failed IVR transcripts: About forty messages are failed IVR transcripts (mentioned in email thread)
7. Ticket auto-closure: Tickets auto-closed after 72 hours without customer reply are recorded as closed but surveyed

### Completed Task
- Created 10-bullet summary of SLA targets, cost figures, shift definitions, and data traps as requested
- Summary saved to summary.txt
- first summary missed the resolving-agent rule and the email thread; asked for a correction

### Data Cleaning Performed
- Removed duplicate tickets: 616 duplicate rows removed based on ticket_id, leaving 11,200 unique tickets.
- Converted timestamps from UTC to IST (UTC+5:30) for created_at, first_response_at, resolved_at fields.
- Treated legacy CSAT of 0 as blank (set csat_score to empty string where value was "0").
- Flagged failed IVR transcripts: added column 'ivr_failed' with 'Y' for rows where customer_message contains "[IVR transcript]", else blank.
- Wrote cleaned data to new file: tickets_cleaned.csv (original tickets.csv preserved).
- Verified before/after counts and sampled rows.

### Duplicate Handling Details
- Of the 616 duplicate ticket_ids, the two copies were **not identical**.
- Differences were consistently in:
    * `source_system`: one copy marked `helpdesk`, the other `legacy_fd` (indicating migration re-import).
    * `csat_score`: in 336 of the duplicate pairs, the legacy_fd copy had `csat_score = "0"` while the helpdesk copy had a blank value (no response).
- The cleaning script kept the **first occurrence** of each ticket_id as it appeared in the original `tickets.csv`.
- Inspection of the original file shows that the helpdesk version typically appears before its legacy_fd duplicate, so the retained row is the helpdesk version (source_system=helpdesk, csat blank).
- This approach aligns with the policy guidance to treat legacy CSAT of 0 as blank and prefers the newer helpdesk data over the legacy duplicate.

### Breach Analysis (using tickets_cleaned.csv)
**Methodology**
- Response time = first_response_at − created_at (both in IST after cleaning).
- Channel‑specific targets: chat 15 min, voice 2 h (120 min), social 4 h (240 min), email 8 h (480 min).
- A ticket is a breach if its response time strictly exceeds the target.
- Shift assigned from created_at time in IST:
    * Morning 06:00‑14:00
    * Day 14:00‑22:00
    * Night 22:00‑06:00 (wrap‑around).
- Period split: **before** = created_at < 2025‑07‑01; **after** = created_at ≥ 2025‑07‑01.
- Tier 2 agents (Escalations & Warranty) were identified from agents.csv and excluded from any agent‑level comparison (the requested metrics are not agent‑specific, so all tickets were used for the breach rates shown below).
- Duplicate rule applied: keep the helpdesk row (source_system = helpdesk) when both helpdesk and legacy_fd rows exist; fall back to legacy only if no helpdesk row exists.

**Results**
- **Breach rate by month (percentage)** – shows a clear increase after mid‑2025, coinciding with the policy‑noted rise in SLA credits.
    * 2025‑01: 8.20 % (21/256)
    * 2025‑02: 11.33 % (41/362)
    * 2025‑03: 9.11 % (37/406)
    * 2025‑04: 9.09 % (38/418)
    * 2025‑05: 9.55 % (40/419)
    * 2025‑06: 8.40 % (34/405)
    * 2025‑07: 22.95 % (109/475)
    * 2025‑08: 27.49 % (188/684)
    * 2025‑09: 26.69 % (182/682)
    * 2025‑10: 23.99 % (207/863)
    * 2025‑11: 24.28 % (212/873)
    * 2025‑12: 23.33 % (195/836)
    * 2026‑01: 25.94 % (213/821)
    * 2026‑02: 22.82 % (157/688)
    * 2026‑03: 25.96 % (203/782)
    * 2026‑04: 26.76 % (194/725)
    * 2026‑05: 25.17 % (188/747)
    * 2026‑06: 23.88 % (181/758)

- **Breach rate by shift before 2025‑07‑01**
    * Morning: 9.11 % (77/845)
    * Day:   8.80 % (82/932)
    * Night: 10.63 % (52/489)

- **Breach rate by shift after 2025‑07‑01**
    * Morning: 9.90 % (317/3201)
    * Day:   8.91 % (333/3736)
    * Night: 79.07 % (1579/1997)

- **Breach rate by shift and channel after 2025‑07‑01**
    * Day - chat:      8.09 % (126/1557)
    * Day - email:    12.25 % (134/1094)
    * Day - social:    8.31 % (30/361)
    * Day - voice:     5.94 % (43/724)
    * Morning - chat:  9.41 % (126/1339)
    * Morning - email: 12.99 % (135/1039)
    * Morning - social: 8.96 % (31/346)
    * Morning - voice:  5.24 % (25/477)
    * Night - chat:   100.00 % (1034/1034)
    * Night - email:   49.68 % (387/779)
    * Night - social:  85.87 % (158/184)
    * (Night - voice not shown because no voice tickets in the sample after the cutoff; if present, would be processed similarly.)

**Observations**
- The night shift shows exceptionally high breach rates after mid‑2025, especially for chat (100 %). This reflects either a genuine lack of night‑shift chat coverage or a data‑quality issue (e.g., missing first_response_at for night‑shift chats). The policy’s shift definitions and the email thread’s mention of timezone mismatches should be kept in mind when interpreting these numbers.
- Morning and day shifts remain relatively stable (≈9 % and ≈9 % breach rates) before and after the cutoff, suggesting that the SLA deterioration is concentrated in the night shift.
- The overall monthly breach rate roughly triples from early‑2025 levels to mid‑2026 levels, consistent with the finance controller’s observation that the SLA credit line in the P&L has tripled since last summer.

All calculations, assumptions, and intermediate steps are documented in the script `compute_breaches.py` and the cleaned file `tickets_cleaned.csv`. The original `tickets.csv` remains unchanged.


### Weekly Breach Report Generation (Updated v3)
- Updated script `weekly_breach_report_v3.py` to implement three requested changes:
  1. **Shift table**: added columns `no_cover_breaches`, `staffed_late_breaches`, `total_breaches` (sum of the two), and a `partial_week` flag indicating the final week (week of 2026-06-29) which contains only one day of data and is marked as partial.
  2. **Agent view**: removed noisy weekly agent rows from HTML; retained full detail in `weekly_agent_report_detailed.csv`. Added two summary tables:
     - Whole‑period Tier 1 agent summary (`weekly_agent_report_summary.csv`) showing breach rate only for agents with ≥20 tickets.
     - Last‑4‑weeks Tier 1 agent summary (`weekly_agent_report_last4weeks_summary.csv`) with the same ≥20‑ticket threshold.
     Both summaries include `breach_rate_%`, `staffed_late_rate_%`, and the `mostly_inherited_flag`.
     Tier 2 agents (Escalations & Warranty) are excluded from these summaries and instead listed in `tier2_not_comparable.csv` with a one‑line note explaining why they are not comparable.
  3. **HTML report**: shortened to under ~100 KB. Contains:
     - A note at the top: “Agent figures show who resolved the ticket, not who sent the first reply, because the helpdesk does not record that.”
     - A summary of the last 8 weeks by shift with cause split and total breaches, plus a partial‑week indicator.
     - A table of the top 10 Tier 1 agents by staffed‑late breach rate (staffed_late_breaches / tickets) for agents with at least 20 tickets, showing breach rate, staffed‑late rate, and mostly inherited flag.
     - Links to the CSV files for full detail.
- **Definition of “no cover”**: for a ticket's created date and shift (from `created_at` in IST), check whether at least one agent on the roster from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) is valid on that date and whose shift matches the ticket's shift. If yes → 'staffed but late'; if no → 'no cover'. (Voice has no overnight service by policy, but no voice breaches occur overnight, so nothing changes. A roster row's `to_date` is inclusive.)
- Output files produced:
    * `weekly_shift_report.csv` – weekly shift table with cause split, total breaches, and partial week flag.
    * `weekly_agent_report_detailed.csv` – weekly agent‑level detail (all agents, all weeks).
    * `weekly_agent_report_summary.csv` – agent summary over whole period (Tier 1, min 20 tickets for rates).
    * `weekly_agent_report_last4weeks_summary.csv` – agent summary over last 4 weeks (Tier 1, min 20 tickets for rates).
    * `tier2_not_comparable.csv` – list of Escalations & Warranty agents with explanatory note.
    * `weekly_breach_report.html` – HTML report with summary tables and the note above.
- Script run on 2026-10-01; files created successfully.
- Tier 1 average staffed‑late breach rate (agents with ≥20 tickets): **7.48%**.
- Top three agents by staffed‑late rate:
    * A3003 (Harpreet Deshpande, Chat Frontline): 13.17% (27/205)
    * A3016 (Deepak Jadhav, Email Frontline): 12.28% (7/57)
    * A3001 (Zoya Mehta, Chat Frontline): 12.00% (6/50)
- Breach cause totals by month (no‑cover vs staffed‑late) are shown below for verification.


### Breach Cause Totals by Month (from tickets_cleaned.csv)
Month	No-Cover	Staffed-Late
2025-01	0	21
2025-02	0	41
2025-03	0	37
2025-04	0	38
2025-05	0	40
2025-06	2	32
2025-07	79	30
2025-08	132	56
2025-09	124	58
2025-10	137	70
2025-11	154	58
2025-12	138	57
2026-01	149	64
2026-02	114	43
2026-03	147	56
2026-04	139	55
2026-05	136	52
2026-06	130	51
### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. To achieve full night coverage, we assume we can assign any spare frontline agent to cover all missing nights (simplification).
11. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 362
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

- Extra agents needed to achieve full night coverage: 1
- Cost of extra agent(s) per quarter: Rs 120,780
- Avoidable credit saving per quarter: Rs 115,757
- Net saving per quarter: Rs -5,023

- Impact on day/morning coverage if reassigning agents: One fewer frontline agent available for day/morning shifts (spare agents reduced from 26 to 25)

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches: 9.48%
- Reduction in overall breach rate: 15.60 percentage points

### Headline Goal
Cut the overall breach rate from 25.08% to 9.48%, worth about Rs 115,757 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. To achieve full night coverage, we assume we can assign any spare frontline agent to cover all missing nights (simplification).
11. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 362
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

- Extra agents needed to achieve full night coverage: 1
- Cost of extra agent(s) per quarter: Rs 120,780
- Avoidable credit saving per quarter: Rs 115,757
- Net saving per quarter: Rs -5,023

- Impact on day/morning coverage if reassigning agents: One fewer frontline agent available for day/morning shifts (spare agents reduced from 26 to 25)

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches: 9.48%
- Reduction in overall breach rate: 15.60 percentage points

### Headline Goal
Cut the overall breach rate from 25.08% to 9.48%, worth about Rs 115,757 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. To achieve full night coverage, we assume we can assign any spare frontline agent to cover all missing nights (simplification).
11. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Breaches avoided: 1306
  Credit saved per year: Rs 457,100
  Credit saved per quarter: Rs 114,275

Option 2: Agent covers 22:00 to 04:00
  Breaches avoided: 1403
  Credit saved per year: Rs 491,050
  Credit saved per quarter: Rs 122,762

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Breaches avoided: 990
  Credit saved per year: Rs 346,500
  Credit saved per quarter: Rs 86,625

Hourly share of overnight tickets (all night shift tickets):
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)
  06:00 - 06:59: 0.00% (0 tickets)
  07:00 - 07:59: 0.00% (0 tickets)
  08:00 - 08:59: 0.00% (0 tickets)
  09:00 - 09:59: 0.00% (0 tickets)
  10:00 - 10:59: 0.00% (0 tickets)
  11:00 - 11:59: 0.00% (0 tickets)
  12:00 - 12:59: 0.00% (0 tickets)
  13:00 - 13:59: 0.00% (0 tickets)
  14:00 - 14:59: 0.00% (0 tickets)
  15:00 - 15:59: 0.00% (0 tickets)
  16:00 - 16:59: 0.00% (0 tickets)
  17:00 - 17:59: 0.00% (0 tickets)
  18:00 - 18:59: 0.00% (0 tickets)
  19:00 - 19:59: 0.00% (0 tickets)
  20:00 - 20:59: 0.00% (0 tickets)
  21:00 - 21:59: 0.00% (0 tickets)
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Extra cost per quarter: Rs 120,780
  Avoidable credit saving per quarter: Rs 115,757
  Net saving per quarter: Rs -5,023

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter: Rs 115,757
  Net saving per quarter: Rs 115,757 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.
  (Assuming we have a spare agent to reassign; current spare frontline agents: 44)

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches: 9.48%
- Reduction in overall breach rate: 15.60 percentage points

### Headline Goal
Cut the overall breach rate from 25.08% to 9.48%, worth about Rs 115,757 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Tickets in window: 1513
  Actual breaches in window: 1306
  Expected breaches in window: 143.46
  Breaches avoided: 1162.54 => 1163
  Credit saved per year: Rs 406,889
  Credit saved per quarter: Rs 101,722

Option 2: Agent covers 22:00 to 04:00
  Tickets in window: 1699
  Actual breaches in window: 1403
  Expected breaches in window: 161.10
  Breaches avoided: 1241.90 => 1242
  Credit saved per year: Rs 434,666
  Credit saved per quarter: Rs 108,667

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Tickets in window: 991
  Actual breaches in window: 990
  Expected breaches in window: 93.97
  Breaches avoided: 896.03 => 896
  Credit saved per year: Rs 313,612
  Credit saved per quarter: Rs 78,403

Hourly share of overnight tickets (night hours only):
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Extra cost per quarter: Rs 120,780
  Avoidable credit saving per quarter (baseline-adjusted best option): Rs 108,667
  Net saving per quarter: Rs -5,023

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter (baseline-adjusted best option): Rs 108,667
  Net saving per quarter: Rs 108,667 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches (baseline): 9.48%
- Overall breach rate after best option (22:00-04:00): 10.44%
- Reduction in overall breach rate (baseline): 15.60 percentage points
- Reduction in overall breach rate (best option): 10.44 percentage points

### Headline Goal
Cut the overall breach rate from about 25.1% to about 10.4%, worth roughly Rs 108,667 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Tickets in window: 1513
  Actual breaches in window: 1306
  Expected breaches in window: 143.46
  Breaches avoided: 1162.54 => 1163
  Credit saved per year: Rs 406,889
  Credit saved per quarter: Rs 101,722

Option 2: Agent covers 22:00 to 04:00
  Tickets in window: 1699
  Actual breaches in window: 1403
  Expected breaches in window: 161.10
  Breaches avoided: 1241.90 => 1242
  Credit saved per year: Rs 434,666
  Credit saved per quarter: Rs 108,667

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Tickets in window: 991
  Actual breaches in window: 990
  Expected breaches in window: 93.97
  Breaches avoided: 896.03 => 896
  Credit saved per year: Rs 313,612
  Credit saved per quarter: Rs 78,403

Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00
  Tickets in window: 1040
  Actual breaches in window: 1035
  Expected breaches in window: 98.61
  Breaches avoided: 936.39 => 936
  Credit saved per year: Rs 327,736
  Credit saved per quarter: Rs 81,934

Hourly share of overnight tickets (night hours only):
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Option 1 (22:00-02:00, 4.0h):
    Extra cost per quarter: Rs 60,390
    Avoidable credit saving per quarter: Rs 101,722
    Net saving per quarter: Rs 41,332

  Option 2 (22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 108,667
    Net saving per quarter: Rs 18,082

  Option 3 (chat only 22:00-06:00, 8.0h):
    Extra cost per quarter: Rs 120,780
    Avoidable credit saving per quarter: Rs 78,403
    Net saving per quarter: Rs -42,377

  Option 4 (chat+social 22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 81,934
    Net saving per quarter: Rs -8,651

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter (Option 1): Rs 101,722
  Net saving per quarter: Rs 101,722 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 2): Rs 108,667
  Net saving per quarter: Rs 108,667 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 3): Rs 78,403
  Net saving per quarter: Rs 78,403 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 4): Rs 81,934
  Net saving per quarter: Rs 81,934 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches (baseline): 9.48%
- Overall breach rate after Option 1 (22:00-02:00): 11.37%
- Overall breach rate after Option 2 (22:00-04:00): 10.44%
- Overall breach rate after Option 3 (chat only 22:00-06:00): 14.52%
- Overall breach rate after Option 4 (chat+social 22:00-04:00): 14.04%
- Reduction in overall breach rate (baseline): 15.60 percentage points
- Reduction in overall breach rate (Option 1): 13.71 percentage points
- Reduction in overall breach rate (Option 2): 14.65 percentage points
- Reduction in overall breach rate (Option 3): 10.57 percentage points
- Reduction in overall breach rate (Option 4): 11.04 percentage points

### Headline Goal
Cut the overall breach rate from about 25.1% to about 10.4%, worth roughly Rs 108,667 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Tickets in window: 1513
  Actual breaches in window: 1306
  Expected breaches in window: 143.46
  Breaches avoided: 1162.54 => 1163
  Credit saved per year: Rs 406,889
  Credit saved per quarter: Rs 101,722

Option 2: Agent covers 22:00 to 04:00
  Tickets in window: 1699
  Actual breaches in window: 1403
  Expected breaches in window: 161.10
  Breaches avoided: 1241.90 => 1242
  Credit saved per year: Rs 434,666
  Credit saved per quarter: Rs 108,667

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Tickets in window: 991
  Actual breaches in window: 990
  Expected breaches in window: 93.97
  Breaches avoided: 896.03 => 896
  Credit saved per year: Rs 313,612
  Credit saved per quarter: Rs 78,403

Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00
  Tickets in window: 1040
  Actual breaches in window: 1035
  Expected breaches in window: 98.61
  Breaches avoided: 936.39 => 936
  Credit saved per year: Rs 327,736
  Credit saved per quarter: Rs 81,934

Hourly share of overnight tickets (night hours only):
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Option 1 (22:00-02:00, 4.0h):
    Extra cost per quarter: Rs 60,390
    Avoidable credit saving per quarter: Rs 101,722
    Net saving per quarter: Rs 41,332

  Option 2 (22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 108,667
    Net saving per quarter: Rs 18,082

  Option 3 (chat only 22:00-06:00, 8.0h):
    Extra cost per quarter: Rs 120,780
    Avoidable credit saving per quarter: Rs 78,403
    Net saving per quarter: Rs -42,377

  Option 4 (chat+social 22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 81,934
    Net saving per quarter: Rs -8,651

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter (Option 1): Rs 101,722
  Net saving per quarter: Rs 101,722 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 2): Rs 108,667
  Net saving per quarter: Rs 108,667 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 3): Rs 78,403
  Net saving per quarter: Rs 78,403 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 4): Rs 81,934
  Net saving per quarter: Rs 81,934 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches (baseline): 9.48%
- Overall breach rate after Option 1 (22:00-02:00): 11.37%
- Overall breach rate after Option 2 (22:00-04:00): 10.44%
- Overall breach rate after Option 3 (chat only 22:00-06:00): 14.52%
- Overall breach rate after Option 4 (chat+social 22:00-04:00): 14.04%
- Reduction in overall breach rate (baseline): 15.60 percentage points
- Reduction in overall breach rate (Option 1): 13.71 percentage points
- Reduction in overall breach rate (Option 2): 14.65 percentage points
- Reduction in overall breach rate (Option 3): 10.57 percentage points
- Reduction in overall breach rate (Option 4): 11.04 percentage points

### Headline Goal
Cut the overall breach rate from about 25.1% to about 10.4%, worth roughly Rs 108,667 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Tickets in window: 1513
  Actual breaches in window: 1306
  Expected breaches in window: 143.46
  Breaches avoided: 1162.54 => 1163
  Credit saved per year: Rs 406,889
  Credit saved per quarter: Rs 101,722

Option 2: Agent covers 22:00 to 04:00
  Tickets in window: 1699
  Actual breaches in window: 1403
  Expected breaches in window: 161.10
  Breaches avoided: 1241.90 => 1242
  Credit saved per year: Rs 434,666
  Credit saved per quarter: Rs 108,667

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Tickets in window: 991
  Actual breaches in window: 990
  Expected breaches in window: 93.97
  Breaches avoided: 896.03 => 896
  Credit saved per year: Rs 313,612
  Credit saved per quarter: Rs 78,403

Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00
  Tickets in window: 1040
  Actual breaches in window: 1035
  Expected breaches in window: 98.61
  Breaches avoided: 936.39 => 936
  Credit saved per year: Rs 327,736
  Credit saved per quarter: Rs 81,934

Hourly share of overnight tickets (night hours only):
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Option 1 (22:00-02:00, 4.0h):
    Extra cost per quarter: Rs 60,390
    Avoidable credit saving per quarter: Rs 101,722
    Net saving per quarter: Rs 41,332

  Option 2 (22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 108,667
    Net saving per quarter: Rs 18,082

  Option 3 (chat only 22:00-06:00, 8.0h):
    Extra cost per quarter: Rs 120,780
    Avoidable credit saving per quarter: Rs 78,403
    Net saving per quarter: Rs -42,377

  Option 4 (chat+social 22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 81,934
    Net saving per quarter: Rs -8,651

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter (Option 1): Rs 101,722
  Net saving per quarter: Rs 101,722 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 2): Rs 108,667
  Net saving per quarter: Rs 108,667 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 3): Rs 78,403
  Net saving per quarter: Rs 78,403 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 4): Rs 81,934
  Net saving per quarter: Rs 81,934 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches (baseline): 9.48%
- Overall breach rate after Option 1 (22:00-02:00): 11.37%
- Overall breach rate after Option 2 (22:00-04:00): 10.44%
- Overall breach rate after Option 3 (chat only 22:00-06:00): 14.52%
- Overall breach rate after Option 4 (chat+social 22:00-04:00): 14.04%
- Reduction in overall breach rate (baseline): 15.60 percentage points
- Reduction in overall breach rate (Option 1): 13.71 percentage points
- Reduction in overall breach rate (Option 2): 14.65 percentage points
- Reduction in overall breach rate (Option 3): 10.57 percentage points
- Reduction in overall breach rate (Option 4): 11.04 percentage points

### Headline Goal
Cut the overall breach rate from about 25.1% to about 10.4%, worth roughly Rs 108,667 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Tickets in window: 1513
  Actual breaches in window: 1306
  Expected breaches in window: 143.46
  Breaches avoided: 1162.54 => 1163
  Credit saved per year: Rs 406,889
  Credit saved per quarter: Rs 101,722

Option 2: Agent covers 22:00 to 04:00
  Tickets in window: 1699
  Actual breaches in window: 1403
  Expected breaches in window: 161.10
  Breaches avoided: 1241.90 => 1242
  Credit saved per year: Rs 434,666
  Credit saved per quarter: Rs 108,667

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Tickets in window: 991
  Actual breaches in window: 990
  Expected breaches in window: 93.97
  Breaches avoided: 896.03 => 896
  Credit saved per year: Rs 313,612
  Credit saved per quarter: Rs 78,403

Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00
  Tickets in window: 1040
  Actual breaches in window: 1035
  Expected breaches in window: 98.61
  Breaches avoided: 936.39 => 936
  Credit saved per year: Rs 327,736
  Credit saved per quarter: Rs 81,934

Hourly share of overnight tickets (night hours only):
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Option 1 (22:00-02:00, 4.0h):
    Extra cost per quarter: Rs 60,390
    Avoidable credit saving per quarter: Rs 101,722
    Net saving per quarter: Rs 41,332

  Option 2 (22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 108,667
    Net saving per quarter: Rs 18,082

  Option 3 (chat only 22:00-06:00, 8.0h):
    Extra cost per quarter: Rs 120,780
    Avoidable credit saving per quarter: Rs 78,403
    Net saving per quarter: Rs -42,377

  Option 4 (chat+social 22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 81,934
    Net saving per quarter: Rs -8,651

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter (Option 1): Rs 101,722
  Net saving per quarter: Rs 101,722 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 2): Rs 108,667
  Net saving per quarter: Rs 108,667 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 3): Rs 78,403
  Net saving per quarter: Rs 78,403 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 4): Rs 81,934
  Net saving per quarter: Rs 81,934 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches (baseline): 9.48%
- Overall breach rate after Option 1 (22:00-02:00): 11.37%
- Overall breach rate after Option 2 (22:00-04:00): 10.44%
- Overall breach rate after Option 3 (chat only 22:00-06:00): 14.52%
- Overall breach rate after Option 4 (chat+social 22:00-04:00): 14.04%
- Reduction in overall breach rate (baseline): 15.60 percentage points
- Reduction in overall breach rate (Option 1): 13.71 percentage points
- Reduction in overall breach rate (Option 2): 14.65 percentage points
- Reduction in overall breach rate (Option 3): 10.57 percentage points
- Reduction in overall breach rate (Option 4): 11.04 percentage points

### Headline Goal
Cut the overall breach rate from about 25.1% to about 10.4%, worth roughly Rs 108,667 a quarter.

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Tickets in window: 1513
  Actual breaches in window: 1306
  Expected breaches in window: 143.46
  Breaches avoided: 1162.54 => 1163
  Credit saved per year: Rs 406,889
  Credit saved per quarter: Rs 101,722

Option 2: Agent covers 22:00 to 04:00
  Tickets in window: 1699
  Actual breaches in window: 1403
  Expected breaches in window: 161.10
  Breaches avoided: 1241.90 => 1242
  Credit saved per year: Rs 434,666
  Credit saved per quarter: Rs 108,667

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Tickets in window: 991
  Actual breaches in window: 990
  Expected breaches in window: 93.97
  Breaches avoided: 896.03 => 896
  Credit saved per year: Rs 313,612
  Credit saved per quarter: Rs 78,403

Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00
  Tickets in window: 1040
  Actual breaches in window: 1035
  Expected breaches in window: 98.61
  Breaches avoided: 936.39 => 936
  Credit saved per year: Rs 327,736
  Credit saved per quarter: Rs 81,934

Hourly share of overnight tickets (night hours only):
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Option 1 (22:00-02:00, 4.0h):
    Extra cost per quarter: Rs 60,390
    Avoidable credit saving per quarter: Rs 101,722
    Net saving per quarter: Rs 41,332

  Option 2 (22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 108,667
    Net saving per quarter: Rs 18,082

  Option 3 (chat only 22:00-06:00, 8.0h):
    Extra cost per quarter: Rs 120,780
    Avoidable credit saving per quarter: Rs 78,403
    Net saving per quarter: Rs -42,377

  Option 4 (chat+social 22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 81,934
    Net saving per quarter: Rs -8,651

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter (Option 1): Rs 101,722
  Net saving per quarter: Rs 101,722 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 2): Rs 108,667
  Net saving per quarter: Rs 108,667 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 3): Rs 78,403
  Net saving per quarter: Rs 78,403 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 4): Rs 81,934
  Net saving per quarter: Rs 81,934 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches (baseline): 9.48%
- Overall breach rate after Option 1 (22:00-02:00): 11.37%
- Overall breach rate after Option 2 (22:00-04:00): 10.44%
- Overall breach rate after Option 3 (chat only 22:00-06:00): 14.52%
- Overall breach rate after Option 4 (chat+social 22:00-04:00): 14.04%
- Reduction in overall breach rate (baseline): 15.60 percentage points
- Reduction in overall breach rate (Option 1): 13.71 percentage points
- Reduction in overall breach rate (Option 2): 14.65 percentage points
- Reduction in overall breach rate (Option 3): 10.57 percentage points
- Reduction in overall breach rate (Option 4): 11.04 percentage points

**Note**: Ticket volume doubled from July 2025 across all channels, driven by product VA-EB-PL2. This was not investigated further.

### Headline Goal
Cut the overall breach rate from about 25% to about 11%, worth roughly Rs 101,722 a quarter.


## 2026-10-02

### PII Masking and Model Categorization Experiment

#### Step A-C: PII Masking Completed
- Applied PII masking to  creating 
- Masked: Order IDs (VRxxxxxx) → [ORDER], Email → [EMAIL], Phone → [PHONE], Names after salutations → [NAME]
- Processed all 60 rows
- Verified 0 rows contain remaining order IDs, emails, or phone numbers

#### Step D: Model Classification Attempt
- Used Groq API with model  (due to rate limits on other models)
- Processed all 60 masked customer messages
- Results:
  - Total time: 193.32 seconds (~3.2 minutes)
  - API failures: 0
  - Invalid label format: 39/60 tickets (65%) - model returned empty  field with reasoning in  field
  - Valid label format: 21/60 tickets (35%) - model returned label in  field

#### Reasoning Model Behavior Observed
The  model is a reasoning model that:
- Places its final answer in the  field rather than  field
- Uses chain-of-thought analysis before stating conclusions
- For valid cases: Output format was  in 
- For invalid cases:  field was empty, with full analysis in  field

#### Next Steps for Improved Extraction
To handle reasoning models, extraction logic should:
1. First check  field for label (current approach)
2. If  is empty/invalid, parse  field for conclusions
3. Look for patterns like:
   - "falls under [CATEGORY] category"
   - "[CATEGORY] and a brief reason"
   - Take the last mentioned category in reasoning (often the conclusion)

#### Limitations Noted
- Only 60 tickets available for testing (small sample)
- Labels created by single human annotator (no inter-annotator agreement measured)
- Model only sees masked customer message (no agent notes, bot category, or other metadata)
- Rate limits constrained experimentation with different models



## 2026-10-02

### PII Masking and Model Categorization Experiment

#### Step A-C: PII Masking Completed
- Applied PII masking to `sample_for_labelling.csv` creating `sample_for_labelling_masked.csv`
- Masked: Order IDs (VRxxxxxx) → [ORDER], Email → [EMAIL], Phone → [PHONE], Names after salutations → [NAME]
- Processed all 60 rows
- Verified 0 rows contain remaining order IDs, emails, or phone numbers

#### Step D: Model Classification Attempt
- Used Groq API with model `openai/gpt-oss-20b` (due to rate limits on other models)
- Processed all 60 masked customer messages
- Results:
  - Total time: 193.32 seconds (~3.2 minutes)
  - API failures: 0
  - Invalid label format: 39/60 tickets (65%) - model returned empty `content` field with reasoning in `reasoning` field
  - Valid label format: 21/60 tickets (35%) - model returned label in `content` field

#### Reasoning Model Behavior Observed
The `openai/gpt-oss-20b` model is a reasoning model that:
- Places its final answer in the `reasoning` field rather than `content` field
- Uses chain-of-thought analysis before stating conclusions
- For valid cases: Output format was `"Label\nBrief reason (≤15 words)"` in `content`
- For invalid cases: `content` field was empty, with full analysis in `reasoning` field

#### Next Steps for Improved Extraction
To handle reasoning models, extraction logic should:
1. First check `content` field for label (current approach)
2. If `content` is empty/invalid, parse `reasoning` field for conclusions
3. Look for patterns like:
   - "falls under [CATEGORY] category"
   - "[CATEGORY] and a brief reason"
   - Take the last mentioned category in reasoning (often the conclusion)

#### Limitations Noted
- Only 60 tickets available for testing (small sample)
- Labels created by single human annotator (no inter-annotator agreement measured)
- Model only sees masked customer message (no agent notes, bot category, or other metadata)
- Rate limits constrained experimentation with different models

### Cost of Overnight Coverage Gap Analysis
**Period**: 2025-06-30 to 2026-06-30
**Assumptions**:
1. Only tickets with status 'resolved' or 'closed' considered for breach and credit calculations.
2. Breach defined as first_response_at - created_at > channel target (chat 15min, voice 2h, social 4h, email 8h).
3. 'no cover' breach: no agent from the channel's frontline team (Chat Frontline for chat/social, Email Frontline for email, Voice Frontline for voice) rostered on the ticket's created date and matching shift.
4. Roster row's to_date is inclusive; an agent is valid on a date if from_date <= date <= to_date (or to_date blank).
5. Morning and Day breach rate used as unavoidable baseline for Night tickets.
6. Credit issued per breach regardless of cause, amount Rs 350.
7. Agent cost: Rs 165 per agent-hour, 8-hour shift => Rs 1320 per night shift per agent.
8. Number of nights in period = 366 (one per day).
9. Headcount is frozen; we can only reassign existing agents, not hire new.
10. Average overnight ticket volume per hour computed as total night tickets divided by total night hours (8 hours per night).

**Results**:
- Night 'no cover' breaches (resolved/closed): 1503
- Open or pending tickets excluded: 468
- Credit cost per breach: Rs 350
- Total credit cost (no cover breaches): Rs 526,050
- Credit cost per year: Rs 526,050
- Credit cost per quarter: Rs 131,512

- Morning+Day tickets: 6581
- Morning+Day breaches: 624
- Baseline breach rate (Morning+Day): 9.48%
- Expected Night breaches if same rate: 180.06
- Actual Night breaches: 1503
- Avoidable breaches (actual - expected): 1322.94 => 1323
- Avoidable credit cost per year: Rs 463,029
- Avoidable credit cost per quarter: Rs 115,757

- Cost per agent per night shift: Rs 1,320
- Cost per agent per day: Rs 1,320
- Cost per agent per year: Rs 483,120
- Cost per agent per quarter: Rs 120,780

- Night agents (Chat Frontline, Email Frontline, Voice Frontline) before 2025-06-29: 5
- Night agents (same teams) after 2026-06-30: 0

- Total nights in period: 366
- Nights with at least one frontline night agent rostered: 0
- Coverage proportion: 0.00%

- Average overnight ticket volume per hour: 0.649 tickets/hour
(Total night tickets: 1899, total night hours: 2928)

**Targeted Cover Options Analysis**:
- Night 'no cover' breaches (resolved/closed) in period: 1503

Option 1: Agent covers 22:00 to 02:00
  Tickets in window: 1513
  Actual breaches in window: 1306
  Expected breaches in window: 143.46
  Breaches avoided: 1162.54 => 1163
  Credit saved per year: Rs 406,889
  Credit saved per quarter: Rs 101,722

Option 2: Agent covers 22:00 to 04:00
  Tickets in window: 1699
  Actual breaches in window: 1403
  Expected breaches in window: 161.10
  Breaches avoided: 1241.90 => 1242
  Credit saved per year: Rs 434,666
  Credit saved per quarter: Rs 108,667

Option 3: Agent covers chat only for whole night (22:00-06:00)
  Tickets in window: 991
  Actual breaches in window: 990
  Expected breaches in window: 93.97
  Breaches avoided: 896.03 => 896
  Credit saved per year: Rs 313,612
  Credit saved per quarter: Rs 78,403

Option 4: Chat Frontline agent covering chat and social only, 22:00 to 04:00
  Tickets in window: 1040
  Actual breaches in window: 1035
  Expected breaches in window: 98.61
  Breaches avoided: 936.39 => 936
  Credit saved per year: Rs 327,736
  Credit saved per quarter: Rs 81,934

Hourly share of overnight tickets (night hours only):
  22:00 - 22:59: 38.07% (723 tickets)
  23:00 - 23:59: 21.33% (405 tickets)
  00:00 - 00:59: 11.43% (217 tickets)
  01:00 - 01:59: 8.85% (168 tickets)
  02:00 - 02:59: 5.21% (99 tickets)
  03:00 - 03:59: 4.58% (87 tickets)
  04:00 - 04:59: 4.84% (92 tickets)
  05:00 - 05:59: 5.69% (108 tickets)

**Net Impact**:
- If a new agent is hired for night shift:
  Option 1 (22:00-02:00, 4.0h):
    Extra cost per quarter: Rs 60,390
    Avoidable credit saving per quarter: Rs 101,722
    Net saving per quarter: Rs 41,332

  Option 2 (22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 108,667
    Net saving per quarter: Rs 18,082

  Option 3 (chat only 22:00-06:00, 8.0h):
    Extra cost per quarter: Rs 120,780
    Avoidable credit saving per quarter: Rs 78,403
    Net saving per quarter: Rs -42,377

  Option 4 (chat+social 22:00-04:00, 6.0h):
    Extra cost per quarter: Rs 90,585
    Avoidable credit saving per quarter: Rs 81,934
    Net saving per quarter: Rs -8,651

- If an existing agent is reassigned from day/morning to night shift (no salary change):
  Extra cost per quarter: Rs 0 (same agent)
  Avoidable credit saving per quarter (Option 1): Rs 101,722
  Net saving per quarter: Rs 101,722 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 2): Rs 108,667
  Net saving per quarter: Rs 108,667 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 3): Rs 78,403
  Net saving per quarter: Rs 78,403 (but lose one agent from day/morning shifts)
  Avoidable credit saving per quarter (Option 4): Rs 81,934
  Net saving per quarter: Rs 81,934 (but lose one agent from day/morning shifts)
  Impact: One fewer frontline agent available for day/morning shifts.

- Total tickets (resolved/closed) in period: 8480
- Total breaches (Night + Morning+Day): 2127
- Overall breach rate before fixing gap: 25.08%
- Overall breach rate after eliminating avoidable breaches (baseline): 9.48%
- Overall breach rate after Option 1 (22:00-02:00): 11.37%
- Overall breach rate after Option 2 (22:00-04:00): 10.44%
- Overall breach rate after Option 3 (chat only 22:00-06:00): 14.52%
- Overall breach rate after Option 4 (chat+social 22:00-04:00): 14.04%
- Reduction in overall breach rate (baseline): 15.60 percentage points
- Reduction in overall breach rate (Option 1): 13.71 percentage points
- Reduction in overall breach rate (Option 2): 14.65 percentage points
- Reduction in overall breach rate (Option 3): 10.57 percentage points
- Reduction in overall breach rate (Option 4): 11.04 percentage points

**Note**: Ticket volume doubled from July 2025 across all channels, driven by product VA-EB-PL2. This was not investigated further.

### Headline Goal
Cut the overall breach rate from about 25% to about 11%, worth roughly Rs 101,722 a quarter.


## 2026-10-02

### Task 6 Validation Completed

#### Step A: Reconciliation Checks (All PASSED)
- Duplicate check: 11,200 unique ticket IDs in tickets_cleaned.csv
- Sum check: Weekly shift table sums match overall figures (11,200 tickets, 2,440 breaches)
- Row-level sums: For all rows, no_cover + staffed_late = total breaches
- Time ordering: No ticket has first_response_at earlier than created_at
- Timezone conversion: Every created_at in tickets_cleaned.csv is exactly 5h30m after original tickets.csv
- Date boundary: No no-cover breaches appear before 30 June 2025

#### Step B: Independent Recomputation
- Sample: 30 random tickets (seed: 42)
- Stratification: ≥10 overnight tickets (13 Night shift), ≥5 post-June 30 breaches (13 breaches)
- Error Rate: 0.00% (0 mismatches out of 30 tickets)

#### Step C: Sensitivity Analysis
- Breach rate and quarterly credit under alternative assumptions:
  1. No IST conversion (UTC timestamps): 25.20% breach rate, Rs 27,388 quarterly credit
  2. Duplicates not removed: 25.20% breach rate, Rs 27,388 quarterly credit  
  3. Include open/pending tickets: 24.96% breach rate, Rs 138,338 quarterly credit

#### Step D: Documentation
- Created VALIDATION.md with all checks, error rate, sensitivity table, and known limits
- Known limits documented:
  * Agent table shows resolving agent, not responder
  * 'No cover' rule uses frontline teams by channel
  * Baseline assumes cover brings night tickets to Morning/Day rate
  * AI check used 60 hand-labelled tickets from one labeller
