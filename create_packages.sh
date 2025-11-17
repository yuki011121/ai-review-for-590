#!/bin/bash

# Script to create ZIP packages for each student from blinded reviews
# Run this after rename_and_distribute.sh

TARGET_DIR="./reviews_blinded"
PACKAGES_DIR="./feedback_packages"

# Create packages directory
mkdir -p "$PACKAGES_DIR"

echo "========================================="
echo "Creating feedback packages..."
echo "========================================="
echo "Source: $TARGET_DIR"
echo "Output: $PACKAGES_DIR"
echo ""

# Get unique student IDs from blinded files
STUDENT_IDS=$(ls "$TARGET_DIR" | grep -o '^[^_]*' | sort -u)

PACKAGE_COUNT=0

for student_id in $STUDENT_IDS; do
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
    
    # Create ZIP package
    PACKAGE_NAME="${PACKAGES_DIR}/${student_id}_Feedback_Package.zip"
    cd "$TARGET_DIR"
    zip -q "../${PACKAGE_NAME}" ${student_id}_Review_*.pdf
    cd - > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "✓ Created package for $student_id"
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
echo "3. Use Canvas 'Message Students Who...' feature to notify students"




