# Kia Map & Infotainment Update Checker 🚗🔔

Ein leichtgewichtiges, eigenständiges Python-Skript zur automatischen Überprüfung auf neue Navigations- und Infotainment-Software-Updates für **Kia-Fahrzeuge** (z. B. EV6, EV9, Sportage, Niro, Ceed, etc.) über die offizielle [Kia Update Plattform](https://update.kia.com/EU/DE/search).

Sobald Kia ein neues Update für Ihre Fahrzeug-Identifizierungsnummer (FIN / VIN) freigibt, erhalten Sie automatisch eine detaillierte Benachrichtigung via **Telegram** inklusive Changelog-Link und Download-Informationen.

---

## ✨ Features

- **Offizielle Kia Schnittstelle**: Fragt die Update-Server von Kia direkt anhand der VIN/FIN Ihres Fahrzeugs ab.
- **Keine externen Abhängigkeiten**: Reines Python 3 (`urllib`, `json`, `argparse`). Keine `pip install`-Module erforderlich.
- **Telegram-Benachrichtigung**: Informiert umgehend mit formatiertem Markdown-Bericht über neue Versionen, Build-Nummern und Changelogs.
- **Intelligente Zustandsverwaltung**: Speichert die zuletzt gemeldete Version in `kia_update_state.json` – keine wiederholten Spam-Nachrichten bei unverändertem Stand.
- **Flexible Konfiguration**: Kann über CLI-Argumente, Umgebungsvariablen oder eine `.env`-Datei gesteuert werden.
- **Automatisierungsbereit**: Perfekt für Cronjobs oder systemd-Timer (z. B. monatliche Ausführung).

---

## 🚀 Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/sahnebar/kiamapupdatecheck.git
cd kiamapupdatecheck
```

### 2. Konfiguration anlegen

Kopieren Sie die Vorlage `.env.example` nach `.env`:

```bash
cp .env.example .env
```

Tragen Sie in der `.env`-Datei Ihre Fahrzeug-FIN sowie optional Ihre Telegram-Zugangsdaten ein:

```ini
# Fahrzeug-Identifizierungsnummer (FIN / VIN)
KIA_VIN=KNA... (Ihre 17-stellige FIN)

# Aktuell im Fahrzeug installierte Version (z. B. 07.2026)
KIA_INSTALLED_VERSION=2026.07

# Telegram-Benachrichtigung (Optional)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
TELEGRAM_CHAT_ID=123456789
```

### 3. Skript ausführbar machen & testen

```bash
chmod +x check_kia_update.py

# Status in der Konsole prüfen
./check_kia_update.py --status

# Telegram-Verbindung testen
./check_kia_update.py --test-telegram

# Reguläre Update-Prüfung ausführen
./check_kia_update.py --check
```

---

## 🛠️ Befehlsübersicht (CLI)

| Parameter | Beschreibung |
|---|---|
| `--check` | Führt die reguläre Prüfung durch. Sendet nur bei neuer Version eine Telegram-Meldung (Standard). |
| `--status` | Gibt den lokalen Status sowie die aktuell bei Kia online verfügbare Version in der Konsole aus. |
| `--test-telegram` | Sendet eine Testnachricht an Telegram zur Überprüfung von Bot-Token und Chat-ID. |
| `--force-notify` | Erzwingt das Senden einer Benachrichtigung für die aktuelle Online-Version (Vorschau). |
| `--set-installed <VER>` | Aktualisiert die installierte Baseline-Version nach einem erfolgten Auto-Update (z. B. `08.2026`). |
| `--vin <FIN>` | Übergibt die FIN/VIN direkt als CLI-Parameter statt über `.env`. |
| `--installed <VER>` | Übergibt die installierte Version direkt per Parameter. |
| `--token <TOKEN>` | Übergibt den Telegram-Token per Parameter. |
| `--chat-id <ID>` | Übergibt die Telegram-Chat-ID per Parameter. |

---

## ⏰ Automatisierung (Monatlicher Cronjob)

Um das Skript einmal im Monat automatisch ausführen zu lassen (z. B. am 1. jedes Monats um 09:00 Uhr):

Erstellen Sie eine Datei unter `/etc/cron.d/kia-update-check`:

```cron
# Monatliche Überprüfung am 1. jedes Monats um 09:00 Uhr
0 9 1 * * root /usr/bin/python3 /pfad/zu/kiamapupdatecheck/check_kia_update.py >> /var/log/kia_update.log 2>&1
```

Oder in Ihrer Benutzer-Crontab (`crontab -e`):

```cron
0 9 1 * * /usr/bin/python3 /home/user/kiamapupdatecheck/check_kia_update.py >> /home/user/kiamapupdatecheck/kia_update.log 2>&1
```

---

## 📱 Beispiel einer Telegram-Benachrichtigung

```markdown
🚗 Neues Kia Software-Update verfügbar!

Für Ihren EV6 steht ein neues Infotainment- & Navigations-Update bereit:

• Fahrzeug: EV6 (EV6 2025~2026)
• FIN (VIN): `KNA...`
• System: ccNC Navigation
• Bisher installiert: Veröffentlichungsmonat 07.2026
• Neue Version: Veröffentlichungsmonat 11.2026

Software-Builds:
• CV1.EUR.ccNC.001.002.260915
• CV1.ERT.ccNC_Lite.001.002.260915

📄 Changelog & Details:
Offizielle Kia Update-Mitteilung öffnen

💾 Download:
Über den offiziellen Kia Navigation Updater herunterladen oder im Fahrzeug via OTA prüfen.
```

---

## 🔒 Datenschutz & Sicherheit

- **Keine privaten Daten im Repository**: Die Datei `.env` sowie `kia_update_state.json` sind in `.gitignore` eingetragen und werden niemals versehentlich committet.
- **Sichere Kommunikation**: Alle API-Anfragen an Kia und Telegram erfolgen verschlüsselt über HTTPS.

---

## 📄 Lizenz

Dieses Projekt ist unter der [MIT Lizenz](LICENSE) lizenziert.
