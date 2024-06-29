import json
import csv
import sys
import os

def json_to_csv(json_file):
    # Generate the output CSV filename
    csv_file = os.path.splitext(json_file)[0] + '.csv'

    # Read the JSON file
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Extract the qa_pairs
    qa_pairs = data['documents'][0]['document_content']['qa_pair']

    # Open the CSV file for writing
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write the header
        writer.writerow(['Question', 'Answer'])
        
        # Write each qa_pair to the CSV
        for pair in qa_pairs:
            writer.writerow([pair['question'], pair['answer']])

    print(f"Conversion complete. Output file: {csv_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not json_file.endswith('.json'):
        print("Error: Input file must have a .json extension")
        sys.exit(1)
    
    if not os.path.exists(json_file):
        print(f"Error: File '{json_file}' not found")
        sys.exit(1)
    
    json_to_csv(json_file)
