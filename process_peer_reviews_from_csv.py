#!/usr/bin/env python3
"""
Process Peer Reviews from Google Sheets CSV Export
This script reads the peer review CSV export and generates PDF files for human reviews.

The CSV should have columns like:
- Proposal ID (or Student ID)
- Review content columns
- Reviewer information
"""

import pandas as pd
import os
import sys
import subprocess
import re
import csv
from pathlib import Path

# --- Configuration ---
CSV_FILE = "csv/590-F25_Thesis_Proposal_Review_Revised.csv"  # Updated CSV file
OUTPUT_DIR = "./reviews_original"
PROPOSAL_MAPPING_FILE = "proposal_mapping.csv"  # Maps Proposal ID to Student ID
# --- End Configuration ---

def normalize_text(value: str) -> str:
    """Normalize strings for fuzzy comparison"""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def create_proposal_mapping():
    """Create a mapping file if it doesn't exist"""
    if not os.path.exists(PROPOSAL_MAPPING_FILE):
        print(f"\nCreating {PROPOSAL_MAPPING_FILE}...")
        print("This file maps Proposal IDs from the CSV to Student IDs.")
        print("Format: Proposal_ID,Student_ID,Proposal_Filename")
        print("\nExample:")
        print("123,S01,test.pdf")
        print("456,S02,Yayun's Proposal.pdf")
        
        # Create template
        template = "Proposal_ID,Student_ID,Proposal_Filename\n123,S01,test.pdf\n"
        with open(PROPOSAL_MAPPING_FILE, 'w') as f:
            f.write(template)
        print(f"\n✓ Created template: {PROPOSAL_MAPPING_FILE}")
        print("Please edit it to match your actual Proposal IDs and Student IDs.")
        return None
    
    try:
        mapping_df = pd.read_csv(PROPOSAL_MAPPING_FILE)
        mapping = {}
        title_mapping = {}
        for _, row in mapping_df.iterrows():
            proposal_id = str(row['Proposal_ID']).strip()
            student_id = str(row['Student_ID']).strip()
            title = str(row.get('Proposal_Title', '')).strip()
            
            if proposal_id:
                mapping[proposal_id] = student_id
            if title:
                normalized = normalize_text(title)
                # Favor first occurrence to keep deterministic behavior
                title_mapping.setdefault(normalized, student_id)
        return mapping, title_mapping
    except Exception as e:
        print(f"ERROR reading {PROPOSAL_MAPPING_FILE}: {e}")
        return None, None

def analyze_csv_structure(csv_file):
    """Analyze the CSV structure"""
    try:
        df = pd.read_csv(csv_file)
        print(f"\n✓ Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
        print("\nKey columns found:")
        
        # Look for key columns
        key_cols = {}
        for col in df.columns:
            col_lower = col.lower()
            if 'proposal' in col_lower and 'id' in col_lower:
                key_cols['proposal_id'] = col
            elif 'proposal' in col_lower and 'title' in col_lower:
                key_cols['proposal_title'] = col
            elif 'reviewer' in col_lower:
                # Prioritize columns with 'reviewer' in the name
                key_cols['reviewer'] = col
            elif 'email' in col_lower:
                key_cols['email'] = col
        
        for key, col in key_cols.items():
            print(f"  {key}: {col}")
        
        return df, key_cols
    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        return None, None

def extract_review_content(row, df):
    """
    Extract the full review content from a row.
    Matches CSV column names exactly, no reviewer information, all sections included.
    """
    review_parts = []
    
    # Define sections in order, matching CSV column structure exactly
    sections = [
        ('General Impression & Summary', 'General Impression & Summary', None),
        ('Major Strengths', 'Major Strengths', None),
        ('Key Areas for Improvement', 'Key Areas for Improvement', None),
        ('Title & Abstract Quality', 'Title & Abstract Quality', 'Explanation (Title & Abstract Quality)'),
        ('Introduction & Motivation', 'Introduction & Motivation', 'Explanation (Introduction & Motivation)'),
        ('Background & Related Work', 'Background & Related Work', 'Explanation (Background & Related Work)'),
        ('Thesis Question / Hypothesis & Contribution', 'Thesis Question / Hypothesis & Contribution', 'Explanation (Thesis Question / Hypothesis)'),
        ('Methodology, Design & Validation', 'Methodology, Design & Validation', 'Explanation (Methodology, Design & Validation)'),
        ('Schedule & Feasibility', 'Schedule & Feasibility', 'Explanation (Schedule & Feasibility)'),
        ('Clarity & Style', 'Clarity & Style', 'Explanation (Clarity & Style)'),
        ('Formatting & References', 'Formatting & References', 'Explanation (Formatting & References)'),
        ('Overall Recommendation for the Proposal\'s Outcome', 'Overall Recommendation for the Proposal\'s Outcome', None),
        ('Rate the potential impact/significance of the proposed research', 'Rate the potential impact/significance of the proposed research', None),
        ('Assess the novelty and originality of the following aspects: [Research Question/Hypothesis]', 'Assess the novelty and originality of the following aspects: [Research Question/Hypothesis]', None),
        ('Assess the novelty and originality of the following aspects: [Proposed Methodology]', 'Assess the novelty and originality of the following aspects: [Proposed Methodology]', None),
        ('Assess the novelty and originality of the following aspects: [Potential Contribution]', 'Assess the novelty and originality of the following aspects: [Potential Contribution]', None),
        ('Additional Comments for the Author', 'Additional Comments for the Author', None),
    ]
    
    # Fields that should have question and answer on separate lines
    separate_line_fields = [
        'General Impression & Summary',
        'Major Strengths',
        'Key Areas for Improvement',
        'Additional Comments for the Author'
    ]
    
    # Extract each section in order
    for display_name, col_name, explanation_col in sections:
        if col_name not in df.columns:
            continue
            
        value = str(row[col_name]).strip()
        
        # Skip if empty or nan
        if not value or value == 'nan' or value == '':
            continue
        
        # Format the section - separate line for certain fields
        if display_name in separate_line_fields:
            section_text = f"{display_name}:\n{value}"
        else:
            section_text = f"{display_name}: {value}"
        
        # Add explanation if exists
        if explanation_col and explanation_col in df.columns:
            explanation = str(row[explanation_col]).strip()
            if explanation and explanation != 'nan' and explanation != '':
                section_text += f"\n  - {explanation}"
        
        review_parts.append(section_text)
    
    # Combine all parts with double newline for readability
    full_review = "\n\n".join(review_parts)
    
    # NO reviewer information - removed for anonymity
    return full_review

def save_review_as_pdf(student_id, review_number, review_text, output_dir):
    """Save review text as PDF file"""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{student_id}_H{review_number}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    # First save as text file
    txt_filepath = filepath.replace('.pdf', '.txt')
    with open(txt_filepath, 'w', encoding='utf-8') as f:
        f.write(f"Peer Review for {student_id}\n")  # Anonymized: no review number
        f.write("=" * 60 + "\n\n")
        f.write(review_text)
    
    # Try multiple methods to convert to PDF
    # Method 1: Try pandoc with pdflatex
    try:
        result = subprocess.run(
            ['pandoc', txt_filepath, '-o', filepath, '--pdf-engine=pdflatex'],
            check=True,
            capture_output=True,
            text=True
        )
        os.remove(txt_filepath)  # Remove temp txt file
        return True, filepath
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Method 2: Try pandoc with other engines
    for engine in ['xelatex', 'lualatex', 'wkhtmltopdf']:
        try:
            result = subprocess.run(
                ['pandoc', txt_filepath, '-o', filepath, f'--pdf-engine={engine}'],
                check=True,
                capture_output=True,
                text=True
            )
            os.remove(txt_filepath)
            return True, filepath
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    # Method 3: Try using Python reportlab (if available)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Add title - anonymized: no review number to prevent students from grouping reviews
        title = Paragraph(f"<b>Peer Review for {student_id}</b>", styles['Heading1'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Add content (split by lines, handle special characters)
        for line in review_text.split('\n'):
            if line.strip():
                # Escape HTML special characters
                escaped_line = (line.replace('&', '&amp;')
                               .replace('<', '&lt;')
                               .replace('>', '&gt;'))
                para = Paragraph(escaped_line, styles['Normal'])
                story.append(para)
                story.append(Spacer(1, 6))
        
        doc.build(story)
        os.remove(txt_filepath)
        return True, filepath
    except Exception as e:
        # ReportLab failed, will keep as txt
        pass
    
    # If all methods fail, keep as txt
    return False, txt_filepath

def update_proposal_mapping_reviewer(student_id, source_id, reviewer_name):
    """Update proposal_mapping.csv with reviewer information"""
    if not os.path.exists(PROPOSAL_MAPPING_FILE):
        return
    
    try:
        df = pd.read_csv(PROPOSAL_MAPPING_FILE)
        
        # Add reviewer columns if they don't exist
        for col in ['H1_Reviewer', 'H2_Reviewer', 'AI1_Reviewer', 'AI2_Reviewer']:
            if col not in df.columns:
                df[col] = ''
        
        # Find the row for this student and update the appropriate reviewer column
        mask = df['Student_ID'] == student_id
        if mask.any():
            # Convert to string type to avoid dtype warnings
            df[f'{source_id}_Reviewer'] = df[f'{source_id}_Reviewer'].astype(str)
            df.loc[mask, f'{source_id}_Reviewer'] = reviewer_name
            df.to_csv(PROPOSAL_MAPPING_FILE, index=False)
    except Exception as e:
        print(f"Warning: Could not update reviewer in {PROPOSAL_MAPPING_FILE}: {e}")


def process_reviews():
    """Main function to process reviews from CSV"""
    print("=" * 70)
    print("Process Peer Reviews from CSV")
    print("=" * 70)
    
    # Load CSV
    if not os.path.exists(CSV_FILE):
        print(f"ERROR: {CSV_FILE} not found.")
        return
    
    df, key_cols = analyze_csv_structure(CSV_FILE)
    if df is None:
        return
    
    # Create/get proposal mapping
    proposal_mapping, title_mapping = create_proposal_mapping()
    if proposal_mapping is None:
        print("\n⚠ Please create and edit proposal_mapping.csv first.")
        print("Then run this script again.")
        return
    
    # Group reviews by Proposal ID
    if 'proposal_id' not in key_cols:
        print("ERROR: Could not find 'Proposal ID' column in CSV.")
        print("Available columns:")
        for col in df.columns:
            print(f"  - {col}")
        return
    
    proposal_title_col = key_cols.get('proposal_title')
    reviewer_col = key_cols.get('reviewer')

    proposal_id_col = key_cols['proposal_id']
    reviews_by_proposal = {}
    
    for _, row in df.iterrows():
        proposal_id = str(row[proposal_id_col]).strip()
        
        if not proposal_id or proposal_id == 'nan':
            continue
        
        # Map Proposal ID to Student ID
        student_id = proposal_mapping.get(proposal_id)
        if not student_id and proposal_title_col:
            title_value = str(row[proposal_title_col]).strip()
            normalized = normalize_text(title_value)
            student_id = title_mapping.get(normalized)
        
        if not student_id:
            print(f"⚠ Warning: Proposal ID {proposal_id} not in mapping. Skipping.")
            continue
        
        if student_id not in reviews_by_proposal:
            reviews_by_proposal[student_id] = []
        
        # Extract review content
        review_content = extract_review_content(row, df)
        reviewer_name = ""
        if reviewer_col:
            reviewer_name = str(row.get(reviewer_col, "")).strip()

        reviews_by_proposal[student_id].append({
            'content': review_content,
            'proposal_id': proposal_id,
            'row': row,
            'reviewer_name': reviewer_name
        })
    
    print(f"\n✓ Found reviews for {len(reviews_by_proposal)} students")
    
    # Save reviews as PDF
    print("\n" + "=" * 70)
    print("Generating Review PDFs")
    print("=" * 70)
    
    success_count = 0
    for student_id, reviews in reviews_by_proposal.items():
        if len(reviews) < 1:
            print(f"⚠ {student_id}: No reviews found")
            continue
        elif len(reviews) < 2:
            print(f"⚠ {student_id}: Only 1 review found — duplicating for H2")
            base_name = reviews[0].get('reviewer_name') or "Peer Reviewer 1"
            duplicated = {
                'content': reviews[0]['content'] + "\n\n[Note: Only one human review was submitted. This is a duplicate of Review 1 so that the workflow retains four total reviews.]",
                'proposal_id': reviews[0]['proposal_id'],
                'row': reviews[0]['row'],
                'reviewer_name': f"{base_name} (Duplicate of Review 1)"
            }
            reviews = reviews + [duplicated]
        
        # Take first 2 reviews as H1 and H2 (each proposal should have 2 human reviews)
        for i, review in enumerate(reviews[:2], 1):  # Take first 2
            is_pdf, filepath = save_review_as_pdf(
                student_id, i, review['content'], OUTPUT_DIR
            )
            
            reviewer_name = review.get('reviewer_name') or f"Peer Reviewer {i}"
            update_proposal_mapping_reviewer(student_id, f"H{i}", reviewer_name)

            if is_pdf:
                print(f"✓ {student_id}_H{i}.pdf")
                success_count += 1
            else:
                print(f"✓ {student_id}_H{i}.txt (convert to PDF manually)")
                success_count += 1
    
    print(f"\n✓ Generated {success_count} review files in {OUTPUT_DIR}/")
    print("\nNext steps:")
    print("1. Review the generated files")
    print("2. Convert .txt to .pdf if needed (or install pandoc)")
    print("3. Generate AI reviews using generate_ai_reviews.py")

if __name__ == "__main__":
    process_reviews()

