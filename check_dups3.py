import csv
from collections import defaultdict

def read_tickets(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows

rows = read_tickets('tickets.csv')
by_id = defaultdict(list)
for idx, row in enumerate(rows):
    by_id[row['ticket_id']].append((idx, row))

dup_ids = [tid for tid, lst in by_id.items() if len(lst) > 1]
print(f"Total duplicate ticket_ids: {len(dup_ids)}")

# Collect differences
diff_counts = {}
for tid in dup_ids:
    lst = by_id[tid]
    if len(lst) < 2:
        continue
    first = lst[0][1]
    for i in range(1, len(lst)):
        second = lst[i][1]
        diff_fields = [k for k in first if first[k] != second[k]]
        if diff_fields:
            for k in diff_fields:
                diff_counts[k] = diff_counts.get(k, 0) + 1
            break  # count each duplicate group once

print("Fields that differ among duplicates (number of duplicate groups where field differs):")
for field, count in sorted(diff_counts.items(), key=lambda x: -x[1]):
    print(f"  {field}: {count}")

# Show a few examples for each differing field
examples = {}
for tid in dup_ids:
    if len(examples) >= 5:
        break
    lst = by_id[tid]
    if len(lst) < 2:
        continue
    first = lst[0][1]
    second = lst[1][1]
    diff_fields = [k for k in first if first[k] != second[k]]
    if diff_fields:
        examples[tid] = (first, second, diff_fields)

print("\nExample differences:")
for tid, (first, second, diff_fields) in list(examples.items())[:5]:
    print(f"\nTicket {tid}:")
    for field in diff_fields:
        print(f"  {field}: first='{first[field]}' vs second='{second[field]}'")