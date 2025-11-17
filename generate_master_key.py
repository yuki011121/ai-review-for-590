#!/usr/bin/env python3
"""
Automated Randomization & Key Generation Script
Generates Master_Key.csv by randomizing the public names assigned to 
the four internal review sources for every student.
"""

import csv
import random
import os
import sys

# --- Configuration ---
STUDENT_LIST_FILE = "students.csv"
MASTER_KEY_OUTPUT_FILE = "Master_Key.csv"
SOURCE_DIR = "./reviews_original"

# Define internal source identifiers and their true source type
# 2 Human reviews + 2 AI reviews (4 total per student)
SOURCE_TYPES = {
    "H1": "Human",
    "H2": "Human",
    "AI1": "AI",
    "AI2": "AI"
}

# Define the generic public names students will see
PUBLIC_REVIEW_NAMES = [f"Review_{i}" for i in range(1, len(SOURCE_TYPES) + 1)]

# Optional: Set random seed for reproducibility during testing
# random.seed(42)  # Uncomment for deterministic results
# --- End Configuration ---

def validate_review_files(student_ids):
    """
    Validates that all expected review files exist before generating the master key.
    Returns a list of missing files.
    """
    missing_files = []
    
    for student_id in student_ids:
        for source_id in SOURCE_TYPES.keys():
            expected_file = f"{student_id}_{source_id}.pdf"
            file_path = os.path.join(SOURCE_DIR, expected_file)
            
            if not os.path.exists(file_path):
                missing_files.append(expected_file)
    
    return missing_files

def generate_and_randomize_key():
    """
    Reads student list, validates files, randomizes review assignments, 
    and generates the Master Key CSV.
    """
    
    master_key_data = []
    
    # 1. Read Student IDs
    try:
        with open(STUDENT_LIST_FILE, mode='r', newline='') as infile:
            reader = csv.reader(infile)
            next(reader)  # Skip header row (e.g., 'student_id')
            # Fixed: Properly extract first column from each row
            student_ids = [row[0].strip() for row in reader if row and row[0].strip()]
    except FileNotFoundError:
        print(f"ERROR: {STUDENT_LIST_FILE} not found. Please ensure it exists.")
        sys.exit(1)
    except IndexError:
        print(f"ERROR: {STUDENT_LIST_FILE} appears to be empty or malformed.")
        sys.exit(1)
    
    if not student_ids:
        print(f"ERROR: No student IDs found in {STUDENT_LIST_FILE}.")
        sys.exit(1)
    
    print(f"Found {len(student_ids)} students in {STUDENT_LIST_FILE}")
    
    # 2. Validate that all review files exist
    missing_files = validate_review_files(student_ids)
    
    if missing_files:
        print(f"\nERROR: Missing {len(missing_files)} review file(s):")
        for missing_file in missing_files[:20]:  # Show first 20
            print(f"  - {missing_file}")
        if len(missing_files) > 20:
            print(f"  ... and {len(missing_files) - 20} more")
        print(f"\nPlease ensure all review files are in {SOURCE_DIR} before proceeding.")
        sys.exit(1)
    
    print(f"File validation successful: All {len(student_ids) * len(SOURCE_TYPES)} review files found.")
    
    # 3. Iterate through students and generate randomized assignments
    for student_id in student_ids:
        internal_sources = list(SOURCE_TYPES.keys())
        
        # Create a randomized mapping for the public review names
        randomized_public_names = list(PUBLIC_REVIEW_NAMES)
        random.shuffle(randomized_public_names)
        
        # 4. Pair internal sources with randomized public names
        for i in range(len(internal_sources)):
            internal_id = internal_sources[i]
            public_name = randomized_public_names[i]
            true_source = SOURCE_TYPES[internal_id]
            
            # Internal filename (used by the subsequent shell script)
            internal_filename = f"{student_id}_{internal_id}.pdf"
            
            master_key_data.append({
                "Student_ID": student_id,
                "Internal_Name": internal_filename,
                "True_Source": true_source,
                "Public_Review_Name": public_name
            })
    
    # 5. Write the Master Key CSV file
    fieldnames = ["Student_ID", "Internal_Name", "True_Source", "Public_Review_Name"]
    with open(MASTER_KEY_OUTPUT_FILE, mode='w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master_key_data)
    
    print(f"\n✓ Successfully generated {MASTER_KEY_OUTPUT_FILE}")
    print(f"✓ Created randomized mappings for {len(student_ids)} students")
    print(f"✓ Total review assignments: {len(master_key_data)}")

if __name__ == "__main__":
    generate_and_randomize_key()



