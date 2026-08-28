#!/usr/bin/env bash
# Links this repo's companion/ files into a Keyboard Layers App Companion
# checkout. The app reads config.ini and assets/ relative to its own directory,
# so symlink rather than copy: re-running render-layer-images.sh or editing
# config.ini here then takes effect with no further step.
#
# Usage: tools/install-companion.sh [path-to-app-checkout]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="${1:-$HOME/Development/keyboard_layers_app_companion}"

if [ ! -f "$APP/main.py" ]; then
    echo "Not a companion app checkout: $APP" >&2
    echo "Clone it first: git clone https://github.com/maatthc/keyboard_layers_app_companion.git" >&2
    exit 1
fi

# config.ini is tracked upstream; replacing it leaves that checkout dirty, which
# is harmless but means `git pull` there may need a `git checkout -- config.ini`.
ln -sfn "$REPO/companion/config.ini" "$APP/config.ini"
echo "  config.ini -> companion/config.ini"

mkdir -p "$APP/assets"
for img in "$REPO"/companion/images/kibard-*.png; do
    ln -sfn "$img" "$APP/assets/$(basename "$img")"
    echo "  assets/$(basename "$img") -> companion/images/$(basename "$img")"
done

echo "Linked. Run: cd $APP && python3 main.py --ble"
