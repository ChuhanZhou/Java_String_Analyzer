REPO_URL="https://github.com/kalhauge/jpamb.git"
TEMP_DIR="temp_clone_dir_$$"
TARGET_DIR="benchmark_suite"

echo "start clone from $REPO_URL ..."

echo "step1: clone to $TEMP_DIR ..."
git clone "$REPO_URL" "$TEMP_DIR"

echo "step2: delete git ..."
rm -rf "$TEMP_DIR/.git"

echo "step3: move files to $TARGET_DIR ..."
mkdir -p "$TARGET_DIR"

if command -v rsync >/dev/null 2>&1; then
    rsync -a "$TEMP_DIR"/ "$TARGET_DIR"/
else
    cp -R "$TEMP_DIR"/* "$TARGET_DIR"/ 2>/dev/null || true
    for file in "$TEMP_DIR"/.[!.]*; do
        if [ -e "$file" ]; then
            cp -R "$file" "$TARGET_DIR"/ 2>/dev/null || true
        fi
    done
fi

echo "step4: clear $TEMP_DIR ..."
rm -rf "$TEMP_DIR"

echo "Done!"