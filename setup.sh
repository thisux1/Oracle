#!/usr/bin/env bash

# ─── Oracle V2 Shortcut Installer ───
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Make launcher executable
chmod +x "$PROJECT_DIR/oracle"

echo "Setting up global 'oracle' shortcut..."

ADDED=false

# Setup in ~/.zshrc
if [ -f "$HOME/.zshrc" ]; then
    if ! grep -q "oracle()" "$HOME/.zshrc" && ! grep -q "alias oracle=" "$HOME/.zshrc"; then
        echo -e "\n# ─── Oracle V2 Shortcut ───\noracle() {\n    \"$PROJECT_DIR/oracle\" \"\$@\"\n}" >> "$HOME/.zshrc"
        echo "Global 'oracle' command added to ~/.zshrc"
        ADDED=true
    else
        echo "oracle command already configured in ~/.zshrc"
    fi
fi

# Setup in ~/.bashrc
if [ -f "$HOME/.bashrc" ]; then
    if ! grep -q "oracle()" "$HOME/.bashrc" && ! grep -q "alias oracle=" "$HOME/.bashrc"; then
        echo -e "\n# ─── Oracle V2 Shortcut ───\noracle() {\n    \"$PROJECT_DIR/oracle\" \"\$@\"\n}" >> "$HOME/.bashrc"
        echo "Global 'oracle' command added to ~/.bashrc"
        ADDED=true
    else
        echo "oracle command already configured in ~/.bashrc"
    fi
fi

echo "Setup complete!"
echo "To activate the command in this terminal session, run:"
echo "   source ~/.zshrc    (or source ~/.bashrc)"
echo "Then just type: oracle"
