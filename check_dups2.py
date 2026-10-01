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
print(f"Number of ticket_ids with duplicates: {len(dup_ids)}")
print(f"Total duplicate rows (extra copies): {sum(len(lst)-1 for lst in by_id.values() if len(lst)>1)}")

# Check if any duplicates differ
any_diff = False
diff_examples = []
for tid in dup_ids[:20]:  # check first 20
    lst = by_id[tid]
    if len(lst) < 2:
        continue
    first = lst[0][1]
    for i in range(1, len(lst)):
        second = lst[i][1]
        if first != second:
            any_diff = True
            diff_examples.append((tid, first, second))
            break
    if any_diff:
        break

if any_diff:
    print("Found differing duplicates:")
    for tid, first, second in diff_examples[:3]:
        print(f"\nTicket {tid}:")
        for key in first:
            if first[key] != second[key]:
                print(f"  {key}: '{first[key]}' vs '{second[key]}'")
else:
    print("All duplicate ticket_ids have identical rows (checked first 20 groups).")