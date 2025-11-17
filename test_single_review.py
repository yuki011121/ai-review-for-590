#!/usr/bin/env python3
"""
Test script to generate a single AI review PDF
Tests the updated prompt with no hyphens
"""

import sys
import os

# Add current directory to path to import generate_ai_reviews
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_ai_reviews import generate_reviews_for_student, find_proposal_files, extract_text_from_pdf, call_ai_api, save_review_as_pdf, REVIEW_PROMPT_TEMPLATE, OUTPUT_DIR

def main():
    print("=" * 70)
    print("Testing Single AI Review PDF Generation (No Hyphens)")
    print("=" * 70)
    
    # Find proposal files
    proposal_files = find_proposal_files()
    
    if not proposal_files:
        print(f"\nNo proposal files found in data/")
        return
    
    # Use first student for testing
    student_id, proposal_path = proposal_files[0]
    
    print(f"\nTesting with:")
    print(f"  Student ID: {student_id}")
    print(f"  Proposal: {proposal_path.name}")
    print(f"\nThis will generate 1 AI review (AI1) as PDF file")
    print("=" * 70)
    
    # Extract text from PDF
    print(f"\nReading {proposal_path.name}...")
    proposal_text = extract_text_from_pdf(proposal_path)
    
    if not proposal_text:
        print(f"  ✗ Failed to extract text from {proposal_path}")
        return
    
    print(f"  ✓ Extracted {len(proposal_text)} characters")
    
    # Generate one review
    print(f"\nGenerating AI review 1...")
    review_text = call_ai_api(
        REVIEW_PROMPT_TEMPLATE,
        proposal_text,
        1,
        student_id
    )
    
    if not review_text:
        print(f"  ✗ Failed to generate review")
        return
    
    # Check for hyphens
    if '-' in review_text and 'well-thought-out' in review_text.lower() or 'real-world' in review_text.lower():
        print(f"  ⚠ WARNING: Found hyphens in review text!")
    else:
        print(f"  ✓ No hyphens found in review text")
    
    # Save as PDF
    is_pdf, filepath = save_review_as_pdf(student_id, 1, review_text, OUTPUT_DIR)
    if is_pdf:
        print(f"  ✓ Saved {student_id}_AI1.pdf")
    else:
        print(f"  ✓ Saved {student_id}_AI1.txt (convert to PDF manually)")
    
    print("\n" + "=" * 70)
    print("✓ Test Complete!")
    print("=" * 70)
    print(f"\nGenerated file: {filepath}")
    print("\nPlease verify:")
    print("  1. The review uses first/second person naturally")
    print("  2. No hyphens in compound words (e.g., 'well thought out' not 'well-thought-out')")
    print("  3. Explanation lengths vary appropriately")

if __name__ == "__main__":
    main()


