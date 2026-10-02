---
quick_id: 260618-u6l
slug: ntfy-push-statt-e-mail-im-workflow
date: 2026-06-18
---

# Quick Task 260618-u6l: ntfy-Push statt E-Mail im Workflow

## Ziel

E-Mail-Versand (SendGrid via `dawidd6/action-send-mail@v16`) im GitHub-Actions-Workflow
durch eine ntfy.sh-Push-Benachrichtigung ersetzen. Nur noch Push, kein E-Mail-Kanal mehr.

## Scope

**Datei:** `.github/workflows/catfinder.yml`

### Entfernen
- Kompletter Step `E-Mail senden` (Zeilen 59–70), inkl. aller Mail-Secrets-Referenzen:
  `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM`.

### Hinzufügen
- Neuer Step `Push-Benachrichtigung senden`:
  - `if: steps.catfinder.outputs.new_count > 0` — feuert nur bei neuen Katzen.
  - `curl`-POST an `https://ntfy.sh/${NTFY_TOPIC}` (Topic aus `secrets.NTFY_TOPIC`).
  - Header `Title` = Anzahl neue Katzen, `Priority: high`, `Tags: cat`,
    `Click` = GitHub-Pages-Report-URL (`https://aleks-muc.github.io/catfinder/`).
  - Secret + `new_count` via `env:` injizieren (kein direktes Expression-Interpolieren
    in den Shell-Befehl — vermeidet Script-Injection).

### Unverändert
- Steps `State committen` (Bot-Commit `chore: state & report aktualisiert [skip ci]`),
  `Report für GitHub Pages vorbereiten`, Pages-URL, `permissions: contents: write`.

## Verifikation
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/catfinder.yml'))"` → gültiges YAML.
- Grep: keine Vorkommen von `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM`, `action-send-mail` mehr.
- Bot-Commit-Step (Pfade, Message) byte-identisch zu vorher.

## Nutzer-Aktion danach (außerhalb dieses Tasks)
- GitHub Secret `NTFY_TOPIC` setzen (langer, zufälliger Topic-Name).
- ntfy-App auf demselben Topic abonnieren.
- Alte Mail-Secrets (`SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM`) aus den Repo-Secrets löschen.
- Abgelaufenen SendGrid-Key in der SendGrid-Console widerrufen (nicht nur lokal löschen).
