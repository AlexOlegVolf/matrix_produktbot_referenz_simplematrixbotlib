# EEApp Produktbot

Schlanker Matrix-Bot fuer private, unverschluesselte Direktchats.

## Aufgabe

1. Einladung eines Mitarbeiters vom konfigurierten Firmen-Matrix-Server annehmen.
2. Eine Textnachricht aus einem privaten Zweipersonenraum entgegennehmen.
3. Suchbegriff, Raum und Absender an den n8n-Webhook senden.
4. Das Feld `antwort` aus der n8n-Antwort in denselben Raum senden.

Gruppenraeume, verschluesselte Raeume und Absender anderer Matrix-Server werden ignoriert. Der Bot protokolliert Betrieb und Fehler im systemd-Journal; keine Geheimnisse oder Anfrageinhalte werden geloggt.

## Dateien auf dem Server

`/etc/produktbot/config.env` enthaelt die vier nicht geheimen Werte aus `deploy/config.env.example`.

`/etc/produktbot/matrix-token.secret` enthaelt ausschliesslich den Matrix-Zugriffstoken.

`/etc/produktbot/webhook-key.secret` enthaelt ausschliesslich den n8n-Wert fuer `X-Bot-Key`.

Die beiden `.secret`-Dateien gehoeren niemals in GitHub.
