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
