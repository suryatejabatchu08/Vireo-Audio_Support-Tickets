import os
import time
import json
import csv
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# The 11 valid categories
VALID_CATEGORIES = [
    "Account & Login",
    "App & Firmware",
    "Audio Quality",
    "Billing & Payments",
    "Charging & Battery",
    "Connectivity",
    "Delivery & Shipping",
    "Other",
    "Product Enquiry",
    "Returns & Refunds",
    "Warranty & Repair"
]

# Read the prompt template
with open('prompts/v1.txt', 'r', encoding='utf-8') as f:
    PROMPT_TEMPLATE = f.read().strip()

# Read the masked CSV
MASKED_CSV = 'sample_for_labelling_masked.csv'
rows = []
with open(MASKED_CSV, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

# Models to run
MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-20b"
]

# Output directory for raw responses
RAW_OUTPUT_DIR = 'raw_outputs'
os.makedirs(RAW_OUTPUT_DIR, exist_ok=True)

def call_groq(model, prompt, max_retries=5):
    """Call GROQ API with retry logic for rate limits."""
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 100
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_URL, headers=HEADERS, json=data, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit hit
                wait_time = (2 ** attempt) + 1  # Exponential backoff
                print(f"Rate limit hit for {model}. Waiting {wait_time} seconds before retry {attempt+1}/{max_retries}")
                time.sleep(wait_time)
            else:
                print(f"API error for {model}: {response.status_code} - {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Wait before retry
                else:
                    raise Exception(f"Failed after {max_retries} attempts: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request exception for {model}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    raise Exception(f"Failed to get response from {model} after {max_retries} attempts")

def extract_label_and_reason(text):
    """Extract label and reason from the model's response."""
    lines = text.strip().split('\n')
    if not lines:
        return None, None
    label = lines[0].strip()
    reason = lines[1].strip() if len(lines) > 1 else ""
    # If there are more lines, we only take the first two as per instruction
    return label, reason

def is_valid_label(label):
    """Check if the label is one of the valid categories."""
    return label in VALID_CATEGORIES

def run_model(model_name):
    """Run the model on all tickets and return results."""
    results = []
    failures = []  # list of (ticket_id, error_message)
    invalid_labels = []  # list of (ticket_id, label_returned)

    print(f"\nRunning model: {model_name}")
    start_time = time.time()

    for i, row in enumerate(rows):
        ticket_id = row['ticket_id']
        message = row['customer_message']

        # Construct the full prompt
        full_prompt = f"{PROMPT_TEMPLATE}\n\nCustomer message:\n{message}"

        try:
            response_json = call_groq(model_name, full_prompt)
            # Extract the assistant's message
            assistant_message = response_json['choices'][0]['message']['content']

            # Save raw response
            raw_file = os.path.join(RAW_OUTPUT_DIR, f"{model_name.replace('/', '_')}_{ticket_id}.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(response_json, f, indent=2)

            # Extract label and reason
            # Add a small delay between requests to avoid hitting rate limits too quickly
            # This is especially important for the free tier
            time.sleep(0.5)  # 500ms delay between requests
            label, reason = extract_label_and_reason(assistant_message)

            if label is None:
                failures.append((ticket_id, "No label extracted"))
                results.append({
                    'ticket_id': ticket_id,
                    'label': None,
                    'reason': None,
                    'valid': False,
                    'error': "No label extracted"
                })
                continue

            valid = is_valid_label(label)
            if not valid:
                invalid_labels.append((ticket_id, label))

            results.append({
                'ticket_id': ticket_id,
                'label': label,
                'reason': reason,
                'valid': valid,
                'error': None
            })

            # Progress indicator
            if (i+1) % 10 == 0:
                print(f"  Processed {i+1}/{len(rows)} tickets")

        except Exception as e:
            failures.append((ticket_id, str(e)))
            results.append({
                'ticket_id': ticket_id,
                'label': None,
                'reason': None,
                'valid': False,
                'error': str(e)
            })
            print(f"  Error processing ticket {ticket_id}: {e}")

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"Completed {model_name} in {elapsed:.2f} seconds")
    print(f"  Failures: {len(failures)}")
    print(f"  Invalid labels: {len(invalid_labels)}")

    return {
        'model': model_name,
        'results': results,
        'failures': failures,
        'invalid_labels': invalid_labels,
        'elapsed_time': elapsed
    }

def main():
    all_results = {}

    for model in MODELS:
        model_results = run_model(model)
        all_results[model] = model_results

        # Save a summary for this model
        summary_file = os.path.join(RAW_OUTPUT_DIR, f"{model.replace('/', '_')}_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'model': model,
                'total_tickets': len(rows),
                'failures': len(model_results['failures']),
                'invalid_labels': len(model_results['invalid_labels']),
                'elapsed_time': model_results['elapsed_time'],
                'failure_details': model_results['failures'],
                'invalid_label_details': model_results['invalid_labels']
            }, f, indent=2)

    # Print overall summary
    print("\n=== SUMMARY ===")
    for model, res in all_results.items():
        print(f"{model}:")
        print(f"  Time: {res['elapsed_time']:.2f}s")
        print(f"  Failures: {len(res['failures'])}")
        print(f"  Invalid labels: {len(res['invalid_labels'])}")
        if res['failures']:
            print(f"  Failure tickets: {[tid for tid, _ in res['failures']]}")
        if res['invalid_labels']:
            print(f"  Invalid label tickets: {[tid for tid, _ in res['invalid_labels']]}")

if __name__ == '__main__':
    main()