import csv
from collections import defaultdict

def read_tickets(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames

rows, _ = read_tickets('tickets.csv')
# group by ticket_id
by_id = defaultdict(list)
for idx, row in enumerate(rows):
    by_id[row['ticket_id']].append((idx, row))

dup_counts = {tid: len(lst) for tid, lst in by_id.items() if len(lst) > 1}
print(f"Total duplicate ticket_ids: {len(dup_counts)}")
total_dup_rows = sum(cnt-1 for cnt in dup_counts.values())
print(f"Total duplicate rows (extra copies): {total_dup_rows}")

# For a few duplicates, compare rows
examples = []
for tid, lst in list(by_id.items())[:5]:
    if len(lst) > 1:
        examples.append((tid, lst))

print("\nChecking first few duplicate groups for differences:")
for tid, entries in examples:
    print(f"\nTicket {tid} has {len(entries)} copies:")
    # compare all fields
    first_row = entries[0][1]
    for i, (orig_idx, row) in enumerate(entries[1:], start=1):
        diff_fields = []
        for key in first_row:
            if first_row[key] != row[key]:
                diff_fields.append(key)
        if diff_fields:
            print(f"  Copy {i+1} (original row index {orig_idx}) differs in fields: {diff_fields}")
            # show a couple differing values
            for key in diff_fields[:3]:
                print(f"    {key}: first='{first_row[key]}' vs copy='{row[key]}'")
        else:
            print(f"  Copy {i+1} (original row index {orig_idx}) is identical.")