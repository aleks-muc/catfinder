---
quick_id: 260618-u6l
slug: ntfy-push-statt-e-mail-im-workflow
date: 2026-06-18
status: complete
---

# Summary: ntfy-Push statt E-Mail im Workflow

## Was geändert wurde

`.github/workflows/catfinder.yml`: Step `E-Mail senden` (SendGrid via
`dawidd6/action-send-mail@v16`) ersetzt durch Step `Push-Benachrichtigung senden`.

- Feuert nur bei `steps.catfinder.outputs.new_count > 0` (kein Push bei „nichts Neues").
- `curl`-POST an `https://ntfy.sh/${NTFY_TOPIC}`, Topic aus `secrets.NTFY_TOPIC`.
- Header: `Title` = „<n> neue Katze(n)", `Priority: high`, `Tags: cat`,
  `Click` = `https://aleks-muc.github.io/catfinder/`.
- Secret und `new_count` über `env:` injiziert statt direkter Expression-Interpolation
  in den Shell-Befehl (verhindert Script-Injection).
- Mail-Secrets `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM` werden nicht mehr referenziert.

## Verifikation

- YAML mit `yaml.safe_load` geparst → gültig.
- Grep nach `SENDGRID_API_KEY|MAIL_TO|MAIL_FROM|action-send-mail|sendgrid` → 0 Treffer.
- Bot-Commit-Step (`chore: state & report aktualisiert [skip ci]`), Pages-Step und
  State-Commit byte-identisch zu vorher.

## Offene Nutzer-Aktionen (außerhalb des Repos)

1. GitHub Secret `NTFY_TOPIC` setzen — langer, zufälliger Topic-Name (= einziges Geheimnis).
2. ntfy-App (iOS/Android) auf denselben Topic abonnieren.
3. Alte Secrets `SENDGRID_API_KEY`, `MAIL_TO`, `MAIL_FROM` aus den Repo-Secrets entfernen.
4. Abgelaufenen SendGrid-Key in der SendGrid-Console **widerrufen** (nicht nur lokal löschen).
