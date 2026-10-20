#!/bin/sh
# Richtet die werktägliche Stellensuche (7:30) als LaunchAgent ein.
#   tools/launchd/install.sh            einrichten bzw. nach einem Umzug neu einrichten
#   tools/launchd/install.sh entfernen  abschalten
set -eu
LABEL=dev.getyourjob.suche
WURZEL=$(cd "$(dirname "$0")/../.." && pwd)
ZIEL="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
if [ "${1:-}" = "entfernen" ]; then
  rm -f "$ZIEL"
  echo "Stellensuche abgeschaltet."
  exit 0
fi

[ -x "$WURZEL/tools/.venv/bin/python" ] || { echo "tools/.venv fehlt — siehe README"; exit 1; }
mkdir -p "$HOME/Library/Logs/getyourjob" "$HOME/Library/LaunchAgents"
sed -e "s|__WURZEL__|$WURZEL|g" -e "s|__HOME__|$HOME|g" "$WURZEL/tools/launchd/$LABEL.plist" > "$ZIEL"
plutil -lint "$ZIEL" >/dev/null
launchctl bootstrap "$DOMAIN" "$ZIEL"
echo "Eingerichtet: $LABEL (Mo–Fr 7:30), Log: ~/Library/Logs/getyourjob/suche.log"
echo "Sofort testen: launchctl kickstart $DOMAIN/$LABEL"
