import os
import time
import json
import csv
import requests
from datetime import datetime

# Configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set")

OPENROUTER_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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

def call_openrouter(model, prompt, max_retries=5):
    """Call OpenRouter API with retry logic for rate limits."""
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 500
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(OPENROUTER_URL, headers=HEADERS, json=data, timeout=30)
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
    Handles both regular content and reasoning model output.
    """
    # Try to parse as JSON if it looks like JSON response from Groq
    try:
        data = json.loads(text)
        if isinstance(data, dict) and 'choices' in data and len(data['choices']) > 0:
            choice = data['choices'][0]
            message = choice.get('message', {})
            
            # Try content first (for regular models)
            content = message.get('content', '')
            if content and content.strip():
                lines = content.strip().split('
')
                if lines:
                    label = lines[0].strip()
                    reason = lines[1].strip() if len(lines) > 1 else ''
                    return label, reason
            
            # If content is empty or not useful, try reasoning (for reasoning models)
            reasoning = message.get('reasoning', '')
            if reasoning and reasoning.strip():
                # Try to extract label and reason from reasoning text
                lines = reasoning.strip().split('
')
                
                # Look for a line that contains just a label or label followed by explanation
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line:
                        # Skip introductory phrases
                        if line.startswith('We need to classify') or line.startswith('We have categories') or line.startswith('Based on the message'):
                            continue
                        
                        # Check if this line is or contains a valid category label
                        matched_category = None
                        for category in VALID_CATEGORIES:
                            if category == line or line.startswith(category + ':') or line.startswith(category + ' ') or line.endswith(' ' + category) or line.endswith(':' + category):
                                matched_category = category
                                break
                        
                        if matched_category:
                            label = matched_category
                            # Try to find a reason in subsequent lines
                            reason = ''
                            # Look at the next few lines for a reason
                            for j in range(i+1, min(i+4, len(lines))):  # Check up to 3 lines ahead
                                reason_line = lines[j].strip()
                                if reason_line and not reason_line.startswith('We have categories') and not reason_line.startswith('Based on the message'):
                                    # Skip if it looks like another category label
                                    is_another_category = any(cat == reason_line or cat in reason_line for cat in VALID_CATEGORIES)
                                    if not is_another_category:
                                        reason = reason_line
                                        break
                            return label, reason
                
                # If we didn't find a clear label in the lines, look for any category mention
                full_text = ' '.join(lines)
                for category in VALID_CATEGORIES:
                    if category in full_text:
                        label = category
                        # Try to extract a reason - look for text after the category
                        idx = full_text.find(category)
                        if idx != -1:
                            # Get text after the category mention
                            after_category = full_text[idx + len(category):].strip()
                            # Remove common prefixes like colons, dashes
                            after_category = after_category.lstrip(':- ')
                            if after_category:
                                # Take first sentence or up to 15 words
                                words = after_category.split()
                                if len(words) > 15:
                                    reason = ' '.join(words[:15])
                                else:
                                    reason = after_category
                        break
    except json.JSONDecodeError:
        # Not JSON, fall back to regular line parsing
        pass
    except Exception as e:
        print(f'Warning: Error parsing JSON response: {e}')
        # Fall back to regular processing
    
    # Regular processing for non-JSON text or if JSON parsing didn't yield results
    lines = text.strip().split('
')
    if not lines:
        return None, None
    label = lines[0].strip()
    reason = lines[1].strip() if len(lines) > 1 else ''
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
            response_json = call_openrouter(model_name, full_prompt)
            # Extract the assistant's message
            assistant_message = response_json['choices'][0]['message']['content']

            # Save raw response
            raw_file = os.path.join(RAW_OUTPUT_DIR, f"{model_name.replace('/', '_')}_{ticket_id}.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(response_json, f, indent=2)

            # Extract label and reason
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
            # Add a small delay between requests to avoid hitting rate limits too quickly
            # This is especially important for the free tier
            time.sleep(0.5)  # 500ms delay between requests
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