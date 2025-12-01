#!/usr/bin/env python3
"""
Generate AI Reviews for Thesis Proposals
This script reads proposal PDFs from the data/ directory, calls AI APIs to generate
reviews, and saves them as PDF files following the naming convention.

Requirements:
- Proposals should be named as S01.pdf, S02.pdf, etc. in the data/ directory
- Two AI reviews will be generated per proposal
- Output files: S01_AI1.pdf, S01_AI2.pdf in reviews_original/ directory
"""

import os
import sys
import subprocess
from pathlib import Path
import json
import csv
import pandas as pd
import random
import re

# Try to load from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip

# --- Configuration ---
PROPOSALS_DIR = "./data"
OUTPUT_DIR = "./reviews_original"
STUDENT_LIST_FILE = "students.csv"
PROPOSAL_MAPPING_FILE = "proposal_mapping.csv"  # Maps PDF filename to Student ID (optional)

# AI Configuration - Azure OpenAI / Azure AI Foundry (two deployments)
# Model 1: GPT-4o (for AI Review 1)
AZURE_ENDPOINT_1 = os.getenv("AZURE_ENDPOINT_1", "your-azure-endpoint-1")
AZURE_API_KEY_1 = os.getenv("AZURE_API_KEY_1", "your-azure-api-key-1")
AZURE_DEPLOYMENT_1 = os.getenv("AZURE_DEPLOYMENT_1", "gpt-4o-deployment")
AZURE_API_VERSION_1 = os.getenv("AZURE_API_VERSION_1", "2024-02-15-preview")

# Model 2: Llama-3.3-70B-Instruct (for AI Review 2)
AZURE_ENDPOINT_2 = os.getenv("AZURE_ENDPOINT_2", "your-azure-endpoint-2")
AZURE_API_KEY_2 = os.getenv("AZURE_API_KEY_2", "your-azure-api-key-2")
AZURE_DEPLOYMENT_2 = os.getenv("AZURE_DEPLOYMENT_2", "llama-3.3-70b-deployment")
AZURE_API_VERSION_2 = os.getenv("AZURE_API_VERSION_2", "2024-02-15-preview")

# Backward compatibility (use Model 1 as default)
AZURE_ENDPOINT = AZURE_ENDPOINT_1
AZURE_API_KEY = AZURE_API_KEY_1
AZURE_DEPLOYMENT = AZURE_DEPLOYMENT_1
AZURE_API_VERSION = AZURE_API_VERSION_1

# Review prompt template - natural, human-like writing style with first/second person
REVIEW_PROMPT_TEMPLATE = """You are a graduate student providing peer review feedback on a Master's thesis proposal. Write as a real student reviewer would - naturally, using first person ("I", "my") and second person ("your", "you") when appropriate, expressing personal opinions and reactions.

ABSOLUTE REQUIREMENTS - READ THIS FIRST:
- Title & Abstract Quality: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write any descriptive words.
- Introduction & Motivation: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write any descriptive words.
- Background & Related Work: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write any descriptive words.
- Thesis Question / Hypothesis & Contribution: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write "High", "Moderate", "Low", or any other word.
- Methodology, Design & Validation: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write "Good", "High", "Moderate", "Feasible", or any other word.
- Schedule & Feasibility: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write "Moderate", "Feasible", "Realistic", or any other word.
- Clarity & Style: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write any descriptive words.
- Formatting & References: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write "Accept", "Accept (Minor revisions required)", or any other text.
- Rate the potential impact/significance of the proposed research: Write ONLY the number 1, 2, 3, 4, or 5. DO NOT write "Low", "Moderate", "High", "Very High", or any other text.

- Use PLAIN TEXT only - NO markdown formatting (no **, no #, no bullets, no numbered lists)
- ABSOLUTELY NO DASH CHARACTERS of any kind in your response, including:
  * "-" (U+002D, hyphen-minus)
  * "–" (U+2013, en dash)
  * "—" (U+2014, em dash)
  This applies to all words and phrases. If you would normally write "long-term", "state-of-the-art", or use an em dash for emphasis, you MUST rewrite using spaces or punctuation instead (for example: "long term", "state of the art", or a comma).
- ZERO-DASH FINAL CHECK: Before you submit your response, scan what you wrote for "-", "–", and "—". If you find any of them, rewrite those parts so there are absolutely none of these characters in your final answer.
- The ONLY exceptions are:
  * Proper nouns or technical terms that MUST have a dash (e.g., "ML-Agents" as a framework name), and
  * The leading "  - " marker at the start of explanation lines, which is required to match the Google Form format.
- Match the exact structure of human peer reviews from Google Forms
- Do NOT include section numbers, headers like "1.", "2.", etc., or any introductory text
- Start directly with "General Impression & Summary:"
- Use "  - " (two spaces and dash) for explanations under each section
- Each section should have ONLY ONE explanation block starting with "  - "
- Write naturally - don't make every sentence perfect. Use varied sentence structures.

WRITING STYLE GUIDELINES (to sound more human):
- USE FIRST PERSON when expressing personal reactions: "I was surprised...", "I found...", "I think...", "I am curious about...", "I especially liked..."
- USE SECOND PERSON when addressing the author: "your proposal", "your work", "you could..."
- EXPLANATION LENGTH should vary based on interest:
  * For routine/basic sections: 1-2 sentences
  * For interesting sections: 2-3 sentences
  * For very interesting/notable sections: 3-5 sentences
  * Additional Comments: Usually 2-3 sentences if there are comments
- Express personal reactions and opinions naturally
- Use varied vocabulary - don't repeat the same phrases
- Occasionally use slightly informal language (e.g., "could use", "needs more", "pretty good", "I was impressed")
- Some explanations can be longer or shorter - not all need to be perfectly balanced
- It's okay to have minor redundancy or slightly awkward phrasing occasionally
- Use natural transitions and varied sentence beginnings
- Don't make every comment sound like a polished academic statement
- Mix of specific technical comments and general observations with personal reactions
- NEVER use dashes to join words - always write them as separate words (e.g., "well thought out", "real world", "multi agent", "state of the art", "cutting edge", "well suited", "agent based", "reinforcement based", "real time", "cutting edge")
- If you need to describe something, use separate words: "agent based modeling" NOT "agent-based modeling", "well suited" NOT "well-suited"

MANDATORY VALUE RESTRICTIONS (you MUST follow these exactly):
- Title & Abstract Quality: MUST be an integer from 1 to 5 (e.g., "4", "5")
- Introduction & Motivation: MUST be an integer from 1 to 5
- Background & Related Work: MUST be an integer from 1 to 5
- Thesis Question / Hypothesis & Contribution: MUST be an integer from 1 to 5 (e.g., "3", "4", "5") - NOT descriptive words like "High", "Moderate", "Low", etc. ONLY integers 1, 2, 3, 4, or 5.
- Methodology, Design & Validation: MUST be an integer from 1 to 5 (e.g., "3", "4", "5") - NOT descriptive words like "Good", "High", "Moderate", "Feasible", etc. ONLY integers 1, 2, 3, 4, or 5.
- Schedule & Feasibility: MUST be an integer from 1 to 5 (e.g., "3", "4", "5") - NOT descriptive words like "Moderate", "Feasible", "Realistic", etc. ONLY integers 1, 2, 3, 4, or 5.
- Clarity & Style: MUST be an integer from 1 to 5 (e.g., "3", "4", "5") - NOT descriptive words. ONLY integers 1, 2, 3, 4, or 5.
- Formatting & References: MUST be an integer from 1 to 5 (e.g., "3", "4", "5") - NOT text like "Accept", "Accept (Minor revisions required)", etc. ONLY integers 1, 2, 3, 4, or 5.
- Overall Recommendation for the Proposal's Outcome: MUST be one of these EXACT options:
  * "Strongly Accept (No changes needed)"
  * "Accept (Minor revisions required)"
  * "Borderline (Major revisions required)"
  * "Reject (Fundamental issues)"
- Rate the potential impact/significance of the proposed research: MUST be an integer from 1 to 5 (e.g., "3", "4", "5") - NOT text like "Low", "Moderate", "High", "Very High", etc. ONLY integers 1, 2, 3, 4, or 5.
- Assess the novelty and originality of the following aspects: [Research Question/Hypothesis]: MUST be "Low", "Moderate", or "High"
- Assess the novelty and originality of the following aspects: [Proposed Methodology]: MUST be "Low", "Moderate", or "High"
- Assess the novelty and originality of the following aspects: [Potential Contribution]: MUST be "Low", "Moderate", or "High"

Format your response EXACTLY as follows (note: for General Impression, Major Strengths, Key Areas for Improvement, and Additional Comments, put the question on one line and the answer on the next line):

General Impression & Summary:
[2-4 sentences expressing your overall reaction, using first person when appropriate - e.g., "I was surprised this is only a proposal. It already feels very complete and engaging. The work focuses on... The topic is both timely and important."]

Major Strengths:
[2-3 sentences describing strengths, can use "I found", "I especially liked", "your work shows..."]

Key Areas for Improvement:
[1-2 sentences about areas needing work, can use "your proposal could...", "I noticed..."]

Title & Abstract Quality: [MUST be integer 1-5]
  - [1-3 sentences depending on how notable this section is. Use first/second person naturally. E.g., "The title and abstract are excellent. The title clearly states the research focus. The abstract gives a full overview..."]

Introduction & Motivation: [MUST be integer 1-5]
  - [1-3 sentences with personal reaction if notable]

Background & Related Work: [MUST be integer 1-5]
  - [2-4 sentences if this section is interesting or notable. E.g., "The Related Work section is a highlight. The author reviews several representative studies, explains their methods, and points out their weaknesses. This section shows solid understanding and analytical thinking."]

Thesis Question / Hypothesis & Contribution: [MUST be ONLY integer 1, 2, 3, 4, or 5 - NOT "High", "Moderate", "Low", etc.]
  - [2-4 sentences if interesting. E.g., "The proposed contributions are listed in bullet points, which makes them clear and easy to read. I am especially curious about the last contribution, where the author plans to... That idea is both interesting and challenging."]
  Example: "Thesis Question / Hypothesis & Contribution: 4"

Methodology, Design & Validation: [MUST be ONLY integer 1, 2, 3, 4, or 5 - NOT "Good", "High", "Moderate", etc.]
  - [2-3 sentences with your assessment]
  Example: "Methodology, Design & Validation: 4"

Schedule & Feasibility: [MUST be ONLY integer 1, 2, 3, 4, or 5 - NOT "Moderate", "Feasible", "Realistic", etc.]
  - [1-2 sentences, can be brief unless there are concerns]
  Example: "Schedule & Feasibility: 4"

Clarity & Style: [MUST be ONLY integer 1, 2, 3, 4, or 5 - NOT descriptive words]
  - [1-2 sentences about writing quality]
  Example: "Clarity & Style: 4"

Formatting & References: [MUST be ONLY integer 1, 2, 3, 4, or 5 - NOT "Accept", "Accept (Minor revisions required)", etc.]
  Example: "Formatting & References: 3"

Overall Recommendation for the Proposal's Outcome: [MUST be one of: "Strongly Accept (No changes needed)", "Accept (Minor revisions required)", "Borderline (Major revisions required)", "Reject (Fundamental issues)"]

Rate the potential impact/significance of the proposed research: [MUST be ONLY integer 1, 2, 3, 4, or 5 - NOT "Low", "Moderate", "High", "Very High", etc.]
  Example: "Rate the potential impact/significance of the proposed research: 4"

Assess the novelty and originality of the following aspects: [Research Question/Hypothesis]: [MUST be "Low", "Moderate", or "High"]

Assess the novelty and originality of the following aspects: [Proposed Methodology]: [MUST be "Low", "Moderate", or "High"]

Assess the novelty and originality of the following aspects: [Potential Contribution]: [MUST be "Low", "Moderate", or "High"]

Additional Comments for the Author:
[2-3 sentences if you have comments, expressing your overall reaction. E.g., "This is an outstanding proposal. It could serve as an example for other students. Reading it gave me ideas on how to improve my own proposal. Excellent work." OR "None." if no additional comments]

CRITICAL REMINDERS - YOU MUST FOLLOW THESE EXACTLY (THESE ARE MANDATORY, NOT OPTIONAL):
1. Title & Abstract Quality: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use descriptive words. Write ONLY the number, e.g., "Title & Abstract Quality: 4"
2. Introduction & Motivation: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use descriptive words. Write ONLY the number, e.g., "Introduction & Motivation: 4"
3. Background & Related Work: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use descriptive words. Write ONLY the number, e.g., "Background & Related Work: 4"
4. Thesis Question / Hypothesis & Contribution: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use words like "High", "Moderate", "Low", etc. Write ONLY the number, e.g., "Thesis Question / Hypothesis & Contribution: 4"
5. Methodology, Design & Validation: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use words like "Good", "High", "Moderate", "Feasible", etc. Write ONLY the number, e.g., "Methodology, Design & Validation: 4"
6. Schedule & Feasibility: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use words like "Moderate", "Feasible", "Realistic", etc. Write ONLY the number, e.g., "Schedule & Feasibility: 4"
7. Clarity & Style: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use descriptive words. Write ONLY the number, e.g., "Clarity & Style: 4"
8. Formatting & References: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use text like "Accept", "Accept (Minor revisions required)", etc. Write ONLY the number, e.g., "Formatting & References: 3"
9. Rate the potential impact/significance of the proposed research: MUST be ONLY an integer 1, 2, 3, 4, or 5. NEVER use text like "Low", "Moderate", "High", "Very High", etc. Write ONLY the number, e.g., "Rate the potential impact/significance of the proposed research: 4"

If you use any word instead of a number for these fields, your response is WRONG and will be rejected.

Remember: Write as a real graduate student would - use "I" and "you/your" naturally, express personal reactions and opinions, vary explanation length based on how interesting each section is to you. Don't make it sound like a polished academic paper. Keep it constructive but human and personal. Follow ALL value restrictions exactly for the ratings and options. For all rating fields (Title & Abstract Quality, Introduction & Motivation, Background & Related Work, Thesis Question / Hypothesis & Contribution, Methodology, Schedule, Clarity & Style, Formatting & References, and Impact/Significance), use ONLY integers 1-5, nothing else.
"""

# Concise review prompt template - same structure/ratings, much shorter free-text explanations
CONCISE_REVIEW_PROMPT_TEMPLATE = """You are a graduate student providing peer review feedback on a Master's thesis proposal. This time your review should be BRIEF, like a busy student who still gives quick but useful feedback.

ABSOLUTE REQUIREMENTS - READ THIS FIRST:
- You MUST follow all value and option restrictions exactly as in the standard detailed review:
  * All rating fields (Title & Abstract Quality, Introduction & Motivation, Background & Related Work,
    Thesis Question / Hypothesis & Contribution, Methodology, Schedule & Feasibility, Clarity & Style,
    Formatting & References, and Impact/Significance) MUST be integers 1, 2, 3, 4, or 5.
  * Overall Recommendation MUST be one of:
      "Strongly Accept (No changes needed)",
      "Accept (Minor revisions required)",
      "Borderline (Major revisions required)",
      "Reject (Fundamental issues)".
  * Novelty/originality questions MUST use ONLY "Low", "Moderate", or "High".
- Use PLAIN TEXT only - NO markdown formatting.
- ABSOLUTELY NO DASH CHARACTERS of any kind in your response, including:
  * "-" (U+002D, hyphen-minus)
  * "–" (U+2013, en dash)
  * "—" (U+2014, em dash)
  This applies to all words and phrases. If you would normally write "long-term", "state-of-the-art", or use an em dash for emphasis, you MUST rewrite using spaces or punctuation instead (for example: "long term", "state of the art", or a comma).
- ZERO-DASH FINAL CHECK: Before you submit your response, scan what you wrote for "-", "–", and "—". If you find any of them, rewrite those parts so there are absolutely none of these characters in your final answer.
- The ONLY exception is proper nouns or technical terms that MUST have dashes (e.g., "ML-Agents" as a framework name). Do NOT use dashes anywhere else.

CONCISE WRITING STYLE (VERY IMPORTANT):
- This is a SHORT review. Keep free text very brief.
- USE FIRST PERSON for reactions: "I think", "I found", "I liked".
- USE SECOND PERSON when addressing the author: "your proposal", "your work".
- For each explanation section, prefer:
  * One short sentence or
  * A few short phrases or
  * A few words only, if that still feels natural.
- It is OK to omit explanation lines entirely for some rating sections and only give the numeric rating.

Format your response EXACTLY as follows:

General Impression & Summary:
[ONE short sentence or a few phrases only. Example: "Clear proposal on an important topic, mostly well organized."]

Major Strengths:
[A few phrases or ONE short sentence. Example: "Good clarity, solid motivation, clear research direction."]

Key Areas for Improvement:
[A few words or ONE short sentence. Example: "Expand validation plan and clarify data collection steps."]

Title & Abstract Quality: [MUST be integer 1-5]
  - [OPTIONAL: if you add text, keep it to a few words, for example "clear and specific". You may omit this line completely.]

Introduction & Motivation: [MUST be integer 1-5]
  - [OPTIONAL: at most a short phrase, for example "explains why the topic matters". You may omit this line completely.]

Background & Related Work: [MUST be integer 1-5]
  - [OPTIONAL: a short phrase, for example "covers main related work". You may omit this line completely.]

Thesis Question / Hypothesis & Contribution: [MUST be ONLY integer 1, 2, 3, 4, or 5]
  - [OPTIONAL: a short phrase, for example "contributions are mostly clear". You may omit this line completely.]

Methodology, Design & Validation: [MUST be ONLY integer 1, 2, 3, 4, or 5]
  - [OPTIONAL: a short phrase, for example "plan seems realistic". You may omit this line completely.]

Schedule & Feasibility: [MUST be ONLY integer 1, 2, 3, 4, or 5]
  - [OPTIONAL: a short phrase, for example "timeline looks reasonable". You may omit this line completely.]

Clarity & Style: [MUST be ONLY integer 1, 2, 3, 4, or 5]
  - [OPTIONAL: a short phrase, for example "easy to follow". You may omit this line completely.]

Formatting & References: [MUST be ONLY integer 1, 2, 3, 4, or 5]
  - [OPTIONAL: a short phrase, for example "minor format issues only". You may omit this line completely.]

Overall Recommendation for the Proposal's Outcome: [MUST be one of: "Strongly Accept (No changes needed)", "Accept (Minor revisions required)", "Borderline (Major revisions required)", "Reject (Fundamental issues)"]

Rate the potential impact/significance of the proposed research: [MUST be ONLY integer 1, 2, 3, 4, or 5]

Assess the novelty and originality of the following aspects: [Research Question/Hypothesis]: [MUST be "Low", "Moderate", or "High"]

Assess the novelty and originality of the following aspects: [Proposed Methodology]: [MUST be "Low", "Moderate", or "High"]

Assess the novelty and originality of the following aspects: [Potential Contribution]: [MUST be "Low", "Moderate", or "High"]

Additional Comments for the Author:
[Either write "None." or ONE short sentence or a few words, for example "Looking forward to seeing the full thesis."]

CRITICAL REMINDERS:
- All rating and option rules from the standard prompt still apply.
- You may shorten or omit explanation lines, but you MUST NOT change the required rating formats or allowed values.
- Keep the overall length noticeably shorter than a normal, very detailed review.
"""

# Probability that a given student gets one detailed and one concise review (mixed style)
# Example: 0.25 means 75% of students get two detailed reviews, 25% get one detailed + one concise
BRIEF_REVIEW_PROBABILITY = 0.25

# Characters we want to actively strip out from model output for safety
# We treat ALL dash characters as forbidden inside normal text, including:
# - "-" (U+002D, hyphen-minus)
# - "–" (U+2013, en dash)
# - "—" (U+2014, em dash)
# The ONLY allowed dash is the one in the bullet marker "  - " at the start of explanation lines.
FORBIDDEN_DASHES = ["-", "–", "—"]


def remove_forbidden_dashes(text: str) -> str:
    """
    Remove forbidden dash characters from the text while preserving the required
    Google Form-style bullet marker "  - " at the start of explanation lines.

    Strategy:
    1. Temporarily replace any leading "  - " (two spaces, dash, space) at the start
       of a line with a placeholder token so it will not be touched.
    2. Replace ALL occurrences of "-", "–", and "—" with a space.
    3. Restore the placeholder back to "  - ".
    """
    # Step 1: protect bullet markers at the start of lines
    placeholder = "<<BULLET_DASH_PLACEHOLDER>>"
    text = re.sub(r"(^|\n)(  - )", rf"\1{placeholder}", text)

    # Step 2: remove all dash characters everywhere else
    text = re.sub(r"[-–—]", " ", text)

    # Step 3: restore bullet markers
    text = text.replace(placeholder, "  - ")

    return text

# --- End Configuration ---

def load_students():
    """Load student IDs from students.csv"""
    try:
        import pandas as pd
        df = pd.read_csv(STUDENT_LIST_FILE)
        return df['student_id'].astype(str).str.strip().tolist()
    except FileNotFoundError:
        print(f"Warning: {STUDENT_LIST_FILE} not found. Will scan {PROPOSALS_DIR} for PDF files.")
        return None
    except Exception as e:
        print(f"Warning: Could not load {STUDENT_LIST_FILE}: {e}")
        return None

def load_proposal_mapping():
    """Load mapping from PDF filename to Student ID"""
    mapping = {}
    if os.path.exists(PROPOSAL_MAPPING_FILE):
        try:
            import pandas as pd
            df = pd.read_csv(PROPOSAL_MAPPING_FILE)
            for _, row in df.iterrows():
                filename = str(row.get('Proposal_Filename', '')).strip()
                student_id = str(row.get('Student_ID', '')).strip()
                if filename and student_id:
                    mapping[filename] = student_id
            print(f"✓ Loaded {len(mapping)} mappings from {PROPOSAL_MAPPING_FILE}")
        except Exception as e:
            print(f"Warning: Could not load {PROPOSAL_MAPPING_FILE}: {e}")
    return mapping

def find_proposal_files():
    """Find all proposal PDF files in the data directory"""
    proposals_dir = Path(PROPOSALS_DIR)
    if not proposals_dir.exists():
        print(f"ERROR: Directory {PROPOSALS_DIR} not found.")
        return []
    
    # Load mapping if available
    mapping = load_proposal_mapping()
    
    # Find all PDF files
    proposal_files = []
    for pdf_file in proposals_dir.glob("*.pdf"):
        filename = pdf_file.name
        
        # Try to get Student ID from mapping first
        if filename in mapping:
            student_id = mapping[filename]
        elif filename.startswith("S") and len(filename.split("_")[0]) <= 5:
            # Standard format: S01.pdf or S01_something.pdf
            student_id = filename.split("_")[0].replace(".pdf", "")
        else:
            # Use filename as student ID (will need manual mapping)
            student_id = pdf_file.stem
            print(f"⚠ Warning: {filename} doesn't match standard format. Using '{student_id}' as Student ID.")
            print(f"   Consider adding to {PROPOSAL_MAPPING_FILE}")
        
        proposal_files.append((student_id, pdf_file))
    
    return sorted(proposal_files)

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file.
    You may need to install: pip install pypdf2 or pip install pdfplumber
    """
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            print("ERROR: Need either PyPDF2 or pdfplumber installed.")
            print("Install with: pip install pypdf2 or pip install pdfplumber")
            return None
    except Exception as e:
        print(f"ERROR: Could not extract text from {pdf_path}: {e}")
        return None

def call_ai_api(prompt, proposal_text, review_number, student_id):
    """
    Call AI API to generate review.
    Review 1 uses GPT-4o, Review 2 uses Llama-3.3-70B-Instruct
    """
    
    full_prompt = f"{prompt}\n\nProposal Content:\n{proposal_text[:8000]}"
    
    # Review 1 uses GPT-4o
    if review_number == 1:
        print(f"  Using GPT-4o (Endpoint: {AZURE_ENDPOINT_1[:50]}...)")
        return call_azure_openai(
            full_prompt,
            AZURE_ENDPOINT_1,
            AZURE_API_KEY_1,
            AZURE_DEPLOYMENT_1,
            AZURE_API_VERSION_1
        )
    # Review 2 uses Llama-3.3-70B-Instruct
    else:
        print(f"  Using Llama-3.3-70B (Endpoint: {AZURE_ENDPOINT_2[:50]}...)")
        return call_azure_openai(
            full_prompt,
            AZURE_ENDPOINT_2,
            AZURE_API_KEY_2,
            AZURE_DEPLOYMENT_2,
            AZURE_API_VERSION_2
        )

def call_azure_openai(prompt, endpoint, api_key, deployment, api_version):
    """Call Azure OpenAI/AI Foundry API with specific configuration"""
    try:
        from openai import AzureOpenAI
        
        # Handle different endpoint formats
        # Format 1: https://xxx.openai.azure.com/ (standard Azure OpenAI)
        # Format 2: https://xxx.services.ai.azure.com/models/... (Azure AI Foundry)
        if "services.ai.azure.com" in endpoint:
            # Azure AI Foundry format
            # Extract base URL: https://xxx.services.ai.azure.com
            if "/models/" in endpoint:
                base_url = endpoint.split("/models/")[0]
            elif "?" in endpoint:
                base_url = endpoint.split("?")[0].rstrip('/')
            else:
                base_url = endpoint.rstrip('/')
            
            azure_endpoint = base_url
            # For Foundry, use the deployment name as provided
            actual_deployment = deployment
        else:
            # Standard Azure OpenAI format
            azure_endpoint = endpoint.rstrip('/')
            actual_deployment = deployment
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
        )
        
        response = client.chat.completions.create(
            model=actual_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000  # Ensure we get full response
        )
        return response.choices[0].message.content
    except ImportError:
        print("ERROR: Need openai library. Install with: pip install openai")
        return None
    except Exception as e:
        print(f"ERROR calling Azure OpenAI/AI Foundry: {e}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Deployment: {deployment}")
        print(f"  Base URL used: {azure_endpoint if 'azure_endpoint' in locals() else 'N/A'}")
        import traceback
        traceback.print_exc()
        return None

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


def save_review_as_pdf(student_id, review_number, review_text, output_dir):
    """Save review text as PDF file - format matches human review format"""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{student_id}_AI{review_number}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    # First save as text file - format matches human review exactly
    txt_filepath = filepath.replace('.pdf', '.txt')
    with open(txt_filepath, 'w', encoding='utf-8') as f:
        f.write(f"Peer Review for {student_id}\n")  # Anonymized: no review number
        f.write("=" * 60 + "\n\n")
        # Note: AI reviews don't have "Reviewed by:" line, matching the format
        # Human reviews have it because it comes from CSV data
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

def generate_reviews_for_student(student_id, proposal_path):
    """Generate two AI reviews for a single student's proposal"""
    print(f"\nProcessing {student_id}...")
    
    # Extract text from PDF
    print(f"  Reading {proposal_path.name}...")
    proposal_text = extract_text_from_pdf(proposal_path)
    
    if not proposal_text:
        print(f"  ✗ Failed to extract text from {proposal_path}")
        return False
    
    print(f"  ✓ Extracted {len(proposal_text)} characters")
    
    # Decide whether this student gets mixed style (one detailed, one concise)
    use_brief_review = random.random() < BRIEF_REVIEW_PROBABILITY
    if use_brief_review:
        # Randomly choose which review (1 or 2) will use the concise prompt
        brief_review_num = random.choice([1, 2])
        print(f"  Using mixed style: review {brief_review_num} will use CONCISE prompt")
    else:
        brief_review_num = None
        print("  Using detailed style for both AI reviews")
    
    # Generate two reviews
    success_count = 0
    for review_num in [1, 2]:
        print(f"  Generating AI review {review_num}...")
        
        # Choose which prompt template to use for this review
        if use_brief_review and review_num == brief_review_num:
            prompt_template = CONCISE_REVIEW_PROMPT_TEMPLATE
            print("    Prompt style: CONCISE")
        else:
            prompt_template = REVIEW_PROMPT_TEMPLATE
            print("    Prompt style: DETAILED")
        
        review_text = call_ai_api(
            prompt_template,
            proposal_text,
            review_num,
            student_id
        )

        if not review_text:
            print(f"  ✗ Failed to generate review {review_num}")
            continue

        # Enforce removal of all forbidden dash characters as a safety net
        cleaned_text = remove_forbidden_dashes(review_text)
        if cleaned_text != review_text:
            print("  ⚠ Removed dash characters (-, –, —) from review text (bullets preserved).")
        review_text = cleaned_text
        
        # Save as PDF
        is_pdf, filepath = save_review_as_pdf(student_id, review_num, review_text, OUTPUT_DIR)
        reviewer_name = "GPT-4o" if review_num == 1 else "Llama-3.3-70B"
        update_proposal_mapping_reviewer(student_id, f"AI{review_num}", reviewer_name)

        if is_pdf:
            print(f"  ✓ Saved {student_id}_AI{review_num}.pdf")
            success_count += 1
        else:
            print(f"  ✓ Saved {student_id}_AI{review_num}.txt (convert to PDF manually)")
            success_count += 1
    
    return success_count == 2

def main():
    print("=" * 70)
    print("AI Review Generator for Thesis Proposals")
    print("=" * 70)
    
    # Find proposal files
    proposal_files = find_proposal_files()
    
    if not proposal_files:
        print(f"\nNo proposal files found in {PROPOSALS_DIR}")
        print("Expected format: S01.pdf, S02.pdf, etc.")
        return
    
    print(f"\nFound {len(proposal_files)} proposal file(s):")
    for student_id, path in proposal_files:
        print(f"  - {student_id}: {path.name}")
    
    # Confirm before proceeding (skip if running non-interactively)
    print(f"\nThis will generate 2 AI reviews for each proposal ({len(proposal_files) * 2} total reviews)")
    try:
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    except EOFError:
        # Running non-interactively, proceed automatically
        print("Running non-interactively, proceeding automatically...")
    
    # Generate reviews
    print("\n" + "=" * 70)
    print("Generating Reviews")
    print("=" * 70)
    
    success_count = 0
    for student_id, proposal_path in proposal_files:
        if generate_reviews_for_student(student_id, proposal_path):
            success_count += 1
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"✓ Successfully processed: {success_count}/{len(proposal_files)} students")
    print(f"✓ Generated {success_count * 2} review files in {OUTPUT_DIR}/")
    print("\nNext steps:")
    print("1. Teacher will add human reviews (H1, H2) to the same directory")
    print("2. Run: python3 generate_master_key.py")
    print("3. Run: ./rename_and_distribute.sh")

if __name__ == "__main__":
    main()

