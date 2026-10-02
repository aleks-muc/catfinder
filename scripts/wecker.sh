#!/bin/sh
# Startet den täglichen Catfinder-Lauf per workflow_dispatch. Läuft auf dem NAS
# im DSM-Aufgabenplaner, weil GitHub den cron-Start um Stunden verzögert.
# Der Token (fine-grained, nur dieses Repo, Actions: Read and write) liegt
# neben diesem Skript in `github-token`, nur für root lesbar.
TOKEN=$(cat "$(dirname "$0")/github-token") || exit 1

for versuch in 1 2 3; do
  curl -fsS -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -d '{"ref":"main"}' \
    https://api.github.com/repos/aleks-muc/catfinder/actions/workflows/catfinder.yml/dispatches \
    && exit 0
  echo "Versuch $versuch fehlgeschlagen" >&2
  [ "$versuch" -lt 3 ] && sleep 300
done
exit 1
