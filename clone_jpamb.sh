REPO_URL="https://github.com/kalhauge/jpamb.git"
TEMP_DIR="temp_clone_dir_$$"

echo "start clone from $REPO_URL ..."

echo "step1: clone to $TEMP_DIR ..."
git clone "$REPO_URL" "$TEMP_DIR"

echo "step2: delete git ..."
rm -rf "$TEMP_DIR/.git"

echo "step3: delete README.md ..."
rm -rf "$TEMP_DIR/README.md"

echo "step4: move files to ./ ..."
mv "$TEMP_DIR"/* "$TEMP_DIR"/.[!.]* . 2>/dev/null || true

echo "step5: clear $TEMP_DIR ..."
rm -rf "$TEMP_DIR"

echo "Done!"