#!/bin/bash

# Script to create ZIP packages for each student from blinded reviews
# Run this after rename_and_distribute.sh
# Packages are named with student names (Last-First) for easier Canvas upload

TARGET_DIR="./reviews_blinded"
PACKAGES_DIR="./feedback_packages"
STUDENTS_CSV="./students.csv"
MAPPING_CSV="./proposal_mapping.csv"

# Create packages directory
mkdir -p "$PACKAGES_DIR"

# Validate at least one CSV file exists
if [ ! -f "$STUDENTS_CSV" ] && [ ! -f "$MAPPING_CSV" ]; then
    echo "ERROR: Neither students.csv nor proposal_mapping.csv found"
    exit 1
fi

echo "========================================="
echo "Creating feedback packages..."
echo "========================================="
echo "Source: $TARGET_DIR"
echo "Output: $PACKAGES_DIR"
echo ""

# Function to get student name in Last-First format
get_student_name() {
    local student_id=$1
    local author_name=""
    
    # Method 1: Try reading from students.csv first (preferred source)
    if [ -f "$STUDENTS_CSV" ]; then
        # Read students.csv, skip header, find matching student_id
        # Handle Windows line endings (\r\n) by converting to Unix format
        author_name=$(tail -n +2 "$STUDENTS_CSV" | tr -d '\r' | awk -F',' -v id="$student_id" '$1==id {print $2}' | xargs)
    fi
    
    # Method 2: Fallback to proposal_mapping.csv if students.csv is empty or doesn't exist
    if [ -z "$author_name" ] && [ -f "$MAPPING_CSV" ]; then
        # proposal_mapping.csv format: Proposal_ID,Student_ID,Author_Name,Proposal_Title,...
        # Match Student_ID (column 2) and get Author_Name (column 3)
        author_name=$(tail -n +2 "$MAPPING_CSV" | tr -d '\r' | awk -F',' -v id="$student_id" '$2==id {print $3}' | head -1 | xargs)
    fi
    
    if [ -z "$author_name" ]; then
        echo ""
        return 1
    fi
    
    # Convert "First Last" to "Last-First"
    local first_name=$(echo "$author_name" | awk '{print $1}')
    local last_name=$(echo "$author_name" | awk '{for(i=2;i<=NF;i++) printf "%s ", $i; print ""}' | xargs)
    
    # Handle cases where there might be multiple last names
    if [ -z "$last_name" ]; then
        # If only one word, use it as last name
        echo "$author_name"
    else
        echo "${last_name}-${first_name}"
    fi
}

# Get unique student IDs from blinded files
STUDENT_IDS=$(ls "$TARGET_DIR" | grep -o '^[^_]*' | sort -u)

PACKAGE_COUNT=0

for student_id in $STUDENT_IDS; do
    # Get student name in Last-First format
    STUDENT_NAME=$(get_student_name "$student_id")
    
    if [ -z "$STUDENT_NAME" ]; then
        echo "⚠ Warning: No name found for $student_id in students.csv or proposal_mapping.csv, using student_id"
        STUDENT_NAME="$student_id"
    fi
    
    # Find all review files for this student
    REVIEW_FILES=$(ls "$TARGET_DIR/${student_id}_Review_"*.pdf 2>/dev/null)
    
    if [ -z "$REVIEW_FILES" ]; then
        echo "⚠ Warning: No review files found for $student_id"
        continue
    fi
    
    # Count files
    FILE_COUNT=$(echo "$REVIEW_FILES" | wc -l | xargs)
    
    if [ "$FILE_COUNT" -ne 4 ]; then
        echo "⚠ Warning: $student_id has $FILE_COUNT files (expected 4)"
    fi
    
    # Create ZIP package with student name (Last-First format)
    PACKAGE_NAME="${PACKAGES_DIR}/${STUDENT_NAME}_Feedback_Package.zip"
    cd "$TARGET_DIR"
    zip -q "../${PACKAGE_NAME}" ${student_id}_Review_*.pdf
    cd - > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "✓ Created package for $student_id -> $STUDENT_NAME"
        ((PACKAGE_COUNT++))
    else
        echo "✗ Error creating package for $student_id"
    fi
done

echo ""
echo "========================================="
echo "Package creation complete"
echo "========================================="
echo "Total packages created: $PACKAGE_COUNT"
echo "Packages are in: $PACKAGES_DIR"
echo ""
echo "Next steps:"
echo "1. Review packages in $PACKAGES_DIR"
echo "2. Upload each ZIP to Canvas for the corresponding student"




