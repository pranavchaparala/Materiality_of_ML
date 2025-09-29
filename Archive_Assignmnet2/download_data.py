import urllib.request
import json
import os
from io import TextIOWrapper

# --- Configuration ---
# The file that failed to load in your browser: 'flower.ndjson'
DATA_URL = 'https://storage.googleapis.com/quickdraw_dataset/full/simplified/flower.ndjson'
OUTPUT_FILENAME = 'flower_data_local.ndjson'
MAX_LINES_TO_SAVE = 500 

print(f"Starting download of {DATA_URL}...")

# Use try/except for robust error handling, similar to the browser code
try:
    # Open the URL and treat it as a stream
    with urllib.request.urlopen(DATA_URL) as response:
        # Wrap the response stream to decode it as text (utf-8)
        text_stream = TextIOWrapper(response, encoding='utf-8')
        
        # Open a local file to write the results
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as outfile:
            lines_saved = 0
            
            # Read line by line until we reach the limit
            for line in text_stream:
                if lines_saved >= MAX_LINES_TO_SAVE:
                    break
                
                # Optional: Validate the JSON structure before saving (Good practice)
                try:
                    # Check if the line is valid JSON before writing it
                    json.loads(line) 
                    outfile.write(line)
                    lines_saved += 1
                except json.JSONDecodeError:
                    print(f"Skipping malformed line at count {lines_saved}.")

    print(f"\n✅ Success! Saved {lines_saved} lines to '{OUTPUT_FILENAME}'.")
    print(f"You can now open '{OUTPUT_FILENAME}' in VS Code to view the data.")
    
except urllib.error.URLError as e:
    print(f"\n❌ Error connecting to URL: {e.reason}")
except Exception as e:
    print(f"\n❌ An unexpected error occurred: {e}")
