# Vireo Audio: first-response breach report

A small tool that reads Vireo's support tickets and roster and produces a weekly first-response breach report by shift and by agent. It also separates breaches caused by **no one being rostered** from breaches that happened **while the shift was staffed**, and sizes what the overnight coverage gap costs.

## What it found (headline)

- Breaches rose from about 9% to about 25% of tickets after the June 2025 roster change, when the overnight (22:00-06:00 IST) frontline cover was removed.
- Overnight tickets since then breach about 79% of the time (chat about 100%). Morning and Day tickets still breach at about 9%, as before.
- Helpdesk reports credit a breach to the agent who resolved the ticket. For overnight tickets that is almost always a Morning-shift agent, so the morning team is blamed for a gap they did not create.
- Covering 22:00 to 02:00 with one existing agent would avoid roughly 1,160 breaches a year, worth roughly Rs 1.0 lakh a quarter in credits at Rs 350 each.

Full assumptions and sensitivity checks are in `VALIDATION.md` and `LOG.md`.

## Requirements

- Python 3.11 or newer
- The libraries in `requirements.txt`
- The five Vireo data files (not included, see below)

## Setup

1. Create and activate a fresh virtual environment.

   ```
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Place these five files in the `data/` folder. They are client data and are deliberately **not** in this repository.

   - `tickets.csv`
   - `agents.csv`
   - `orders.csv`
   - `customers.csv`
   - `products.csv`

## Run

```
python clean_tickets.py
```

This runs, in order: data cleaning, breach calculation, the weekly reports, and the overnight coverage sizing. Everything is written to `output/`. If a data file is missing, the script says which one and stops.

## What you get in `output/`

**TODO: adjust the file names to match your actual outputs.**

| File | What it is |
|---|---|
| `tickets_cleaned.csv` | Tickets after de-duplication, UTC to IST conversion and CSAT clean-up |
| `weekly_breach_report.html` | Short readable summary: last 8 weeks by shift, top agents by preventable breaches |
| `weekly_shift_report.csv` | Weekly breaches by shift (from ticket creation time, IST), split into "no cover" and "staffed but late" |
| `weekly_agent_report_summary.csv` | Agent totals for the whole period (Tier 1 only, minimum 20 tickets before a rate is shown) |
| `weekly_agent_report_last4weeks_summary.csv` | The same for the last four weeks |
| `weekly_agent_report_detailed.csv` | Weekly agent detail (Tier 1) |
| `tier2_not_comparable.csv` | Escalations & Warranty agents, listed but not compared (policy section 6) |
| `task4_results.txt` | Overnight coverage cost and the four cover options |

## How the main decisions were made

- **Timestamps** in the export are UTC. They are converted to IST (+5h30m) before shifts are assigned.
- **Duplicates** from the migration re-import are removed. The helpdesk row is kept over the legacy row.
- **Legacy CSAT of 0** is treated as no response.
- **Targets** by channel: chat 15 min, voice callback 2 hours, social 4 hours, email 8 hours. A breach is a first response later than the target.
- **Shift** is taken from when the ticket was created, not from who resolved it.
- **"No cover"** means no agent from the channel's frontline team was rostered on that shift on that date. Roster rows are matched by date range, with `to_date` inclusive and blank meaning still active.
- **Tier 2** (Escalations & Warranty) is excluded from agent comparisons.
- **Avoidable breaches** are the overnight breaches above the Morning and Day breach rate (about 9.5%), because some tickets would breach even with cover.
- **Credit cost** is Rs 350 per breach on resolved or closed tickets only. Open and pending tickets are excluded.

## Optional: AI check of the intake bot's category tags

This is a side check. The main report does not need it.

It asks a model to pick a category from the customer's opening message, then compares the result with the bot's tag and with a hand-labelled sample of 60 tickets. Only the customer message is sent, with names, phone numbers, emails and order IDs masked first.

1. Create an Groq key and set it as an environment variable.

   ```
   export GROQ_API_KEY="your_key_here"      # Windows PowerShell: $env:GROQ_API_KEY="your_key_here"
   ```

2. Run the check:

   ```
   python run_classification.py
   ```

If the key is not set, this command says so and stops. The main pipeline is unaffected.

Prompt versions are in `prompts/`. Model names, dates and accuracy are in `LOG.md`.

## Known limits

- **Agent figures show who resolved the ticket**, not who sent the first reply. The helpdesk does not record the second, so agent numbers are an approximation.
- **"No cover" uses frontline teams by channel.** It does not check whether the rostered agent was actually working that hour.
- **The savings estimate assumes** that with cover, overnight tickets would breach at the Morning and Day rate. This is the best case.
- **The effect on day-shift capacity** of moving an agent is not measured here. It needs the team leads' view.
- **The AI check** used 60 tickets labelled by one person, and the model sees only the opening message.
- **Open and pending tickets** are excluded from the credit count. Credits are issued on resolution, so the true figure will rise as they close.

## Repository contents

- `README.md`: this file
- `LOG.md`: decisions, assumptions, prompt versions and what was discarded
- `VALIDATION.md`: checks, error rate on an independent 30-ticket recomputation, and sensitivity analysis
- `prompts/`: AI prompt versions
- `data/`: put the five input files here (not committed)
- `output/`: generated reports (not committed)

## A note on data

All customer, order and agent data belongs to Vireo Audio and is kept out of this repository. Generated reports contain agent names and ticket-derived figures, so `output/` is also not committed.