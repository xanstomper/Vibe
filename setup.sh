#!/bin/bash
echo "Installing Vibe Language..."

# Add to PATH
echo 'export PATH="$HOME/vibe-lang:$PATH"' >> ~/.bashrc
export PATH="$HOME/vibe-lang:$PATH"

echo "Vibe installed!"
echo "Usage:"
echo "  vibec build src/main.vibe    # Build to executable"
echo "  vibec run src/main.vibe      # Run program"
echo "  vibec emit-c src/main.vibe   # Emit C code"
echo "  vpm init                     # Initialize project"
echo "  vpm install <package>        # Install package"
