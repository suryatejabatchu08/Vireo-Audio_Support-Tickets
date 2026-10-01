import csv
import sys
from datetime import datetime, timedelta

def utc_to_ist(utc_str):
    if not utc_str or utc_str.strip() == '':
        return ''
    try:
        dt = datetime.strptime(utc_str.strip(), '%Y-%m-%d %H:%M')
        dt_ist = dt + timedelta(hours=5, minutes=30)
        return dt_ist.strftime('%Y-%m-%d %H:%M')
    except Exception as e:
        # If format unexpected, return original
        return utc_str

def main():
    input_file = 'tickets.csv'
    output_file = 'tickets_cleaned.csv'

    seen_ids = set()
    duplicates_removed = 0
    kept_rows = []

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        # Add new column for ivr flag
        fieldnames = list(fieldnames) + ['ivr_failed']

        for row in reader:
            tid = row['ticket_id']
            if tid in seen_ids:
                duplicates_removed += 1
                continue
            seen_ids.add(tid)

            # Convert timestamps
            for field in ['created_at', 'first_response_at', 'resolved_at']:
                row[field] = utc_to_ist(row[field])

            # Treat legacy CSAT of 0 as blank
            csat = row['csat_score'].strip()
            if csat == '0':
                row['csat_score'] = ''

            # Flag failed IVR transcripts
            cust_msg = row['customer_message']
            if '[IVR transcript]' in cust_msg:
                row['ivr_failed'] = 'Y'
            else:
                row['ivr_failed'] = ''

            kept_rows.append(row)

    # Write cleaned CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    # Print summary
    print(f'Original rows: {len(seen_ids) + duplicates_removed}')
    print(f'Duplicate tickets removed: {duplicates_removed}')
    print(f'Rows kept: {len(kept_rows)}')
    print(f'Cleaned data written to: {output_file}')

    # Show first few rows before and after
    print('\n--- First 3 rows of original (after header) ---')
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for i in range(3):
            try:
                row = next(reader)
                print(row)
            except StopIteration:
                break

    print('\n--- First 3 rows of cleaned (after header) ---')
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for i in range(3):
            try:
                row = next(reader)
                print(row)
            except StopIteration:
                break

if __name__ == '__main__':
    main()