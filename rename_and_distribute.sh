#!/bin/bash

# Configuration
MASTER_KEY_FILE="Master_Key.csv"
SOURCE_DIR="./reviews_original"
TARGET_DIR="./reviews_blinded"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Initialize error tracking
ERROR_COUNT=0
ERROR_LOG="${TARGET_DIR}/rename_errors.log"
SUCCESS_LOG="${TARGET_DIR}/rename_success.log"

# Clear previous logs
> "$ERROR_LOG"
> "$SUCCESS_LOG"

echo "========================================="
echo "Starting batch rename operation..."
echo "========================================="
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo "Master Key: $MASTER_KEY_FILE"
echo ""

# Validate master key exists
if [ ! -f "$MASTER_KEY_FILE" ]; then
    echo "ERROR: Master key file not found: $MASTER_KEY_FILE"
    exit 1
fi

# Count total rows (excluding header)
TOTAL_FILES=$(tail -n +2 "$MASTER_KEY_FILE" | wc -l)
PROCESSED=0

# Skip the header row and read the Master Key CSV line by line
tail -n +2 "$MASTER_KEY_FILE" | while IFS=, read -r student_id internal_name true_source public_review_name reviewer_name; do
    
    # Trim whitespace for accurate file matching
    student_id=$(echo "$student_id" | xargs)
    internal_name=$(echo "$internal_name" | xargs)
    public_review_name=$(echo "$public_review_name" | xargs)
    # Note: reviewer_name is read but not used in filename (for anonymity)
    
    # Construct paths
    SOURCE_PATH="${SOURCE_DIR}/${internal_name}"
    NEW_FILENAME="${student_id}_${public_review_name}.pdf"
    TARGET_PATH="${TARGET_DIR}/${NEW_FILENAME}"
    
    # Execute the rename/copy operation (using cp to preserve originals)
    if [ -f "$SOURCE_PATH" ]; then
        cp "$SOURCE_PATH" "$TARGET_PATH"
        echo "✓ ${internal_name} -> ${NEW_FILENAME}" | tee -a "$SUCCESS_LOG"
        ((PROCESSED++))
    else
        echo "✗ ERROR: Source file not found: ${SOURCE_PATH}" | tee -a "$ERROR_LOG"
        ((ERROR_COUNT++))
    fi
    
done

echo ""
echo "========================================="
echo "Batch renaming complete"
echo "========================================="
echo "Total expected: $TOTAL_FILES"
echo "Successfully processed: $PROCESSED"
echo "Errors: $ERROR_COUNT"
echo ""
echo "Blinded files are in: ${TARGET_DIR}"
echo "Success log: ${SUCCESS_LOG}"

if [ $ERROR_COUNT -gt 0 ]; then
    echo "⚠ WARNING: $ERROR_COUNT files failed to rename"
    echo "Error details: ${ERROR_LOG}"
    exit 1
else
    echo "✓ All files successfully processed"
fi




