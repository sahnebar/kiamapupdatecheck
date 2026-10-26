#!/usr/bin/env python3
"""
Kia Software & Navigation Update Checker
========================================
Prüft auf update.kia.com anhand der Fahrzeug-Identifizierungsnummer (VIN / FIN),
ob ein neues Infotainment-/Navigations-Update für das Fahrzeug bereitsteht.
Benachrichtigt optional via Telegram, sobald eine neuere Version verfügbar ist.

Repository: https://github.com/sahnebar/kiamapupdatecheck
Lizenz: MIT
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime

# Standard-Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "kia_update_state.json")
DEFAULT_ENV_FILE = os.path.join(BASE_DIR, ".env")

# API-Endpunkte
KIA_API_URL = "https://update.kia.com/api/search/vin"
KIA_NOTICE_BASE_URL = "https://update.kia.com/EU/DE/updateNoticeView"
KIA_UPDATER_DOWNLOAD_URL = "https://update.kia.com/EU/DE/navigationUpdate"


def load_env_file(filepath=DEFAULT_ENV_FILE):
    """Einfacher .env-Parser ohne externe Abhängigkeiten."""
    env_vars = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        env_vars[k] = v
        except Exception as e:
            print(f"[WARN] Fehler beim Lesen von {filepath}: {e}", file=sys.stderr)
    return env_vars


def get_config(cli_args, env_vars):
    """
    Kombiniert Konfiguration aus CLI-Parametern, Umgebungsvariablen und .env-Datei.
    Priorität: CLI > OS-Umgebungsvariable > .env Datei > Default.
    """
    def pick(cli_val, env_key, default=""):
        if cli_val is not None and cli_val != "":
            return cli_val
        if os.getenv(env_key):
            return os.getenv(env_key)
        if env_key in env_vars:
            return env_vars[env_key]
        return default

    return {
        "vin": pick(cli_args.vin, "KIA_VIN", ""),
        "installed_version": pick(cli_args.installed, "KIA_INSTALLED_VERSION", "2026.07"),
        "bot_token": pick(cli_args.token, "TELEGRAM_BOT_TOKEN", ""),
        "chat_id": pick(cli_args.chat_id, "TELEGRAM_CHAT_ID", ""),
        "brand": pick(None, "KIA_BRAND", "KM"),
        "region": pick(None, "KIA_REGION", "EU"),
        "lang": pick(None, "KIA_LANG", "DE")
    }


def parse_version_tuple(date_str):
    """
    Konvertiert Datumsangaben wie '2026.07' oder '07.2026' in ein vergleichbares Tuple (YYYY, MM).
    """
    if not date_str:
        return (0, 0)
    parts = date_str.strip().replace("-", ".").replace("/", ".").split(".")
    if len(parts) >= 2:
        try:
            p1, p2 = int(parts[0]), int(parts[1])
            if p1 > 1000:  # Format YYYY.MM
                return (p1, p2)
            else:  # Format MM.YYYY
                return (p2, p1)
        except ValueError:
            pass
    return (0, 0)


def format_month_year(tuple_ym):
    """Gibt 'MM.YYYY' formatiert zurück."""
    y, m = tuple_ym
    if y == 0:
        return "Unbekannt"
    return f"{m:02d}.{y:04d}"


def load_state():
    """Lädt den gespeicherten Zustand (letzte Benachrichtigung, Version)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Konnte State-Datei nicht laden: {e}", file=sys.stderr)
    return {
        "installed_version": None,
        "last_notified_version": None,
        "last_checked": None,
        "latest_data": None
    }


def save_state(state):
    """Speichert den aktuellen Zustand."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Fehler beim Speichern der State-Datei: {e}", file=sys.stderr)


def send_telegram(bot_token, chat_id, text):
    """Sendet eine Nachricht via Telegram Bot API."""
    if not bot_token or not chat_id:
        print("[INFO] Kein Telegram Bot Token oder Chat ID konfiguriert. Überspringe Benachrichtigung.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            return res_data.get("ok", False)
    except Exception as e:
        print(f"[ERROR] Fehler beim Senden der Telegram-Nachricht: {e}", file=sys.stderr)
        return False


def fetch_kia_update_info(config):
    """Ruft die offiziellen Update-Daten von update.kia.com ab."""
    vin = config.get("vin")
    if not vin:
        raise ValueError("Keine FIN/VIN angegeben. Bitte per Parameter --vin, Umgebungsvariable KIA_VIN oder in .env festlegen.")

    payload = {
        "commonCode": {
            "brand": config.get("brand", "KM"),
            "reg": config.get("region", "EU"),
            "lang": config.get("lang", "DE")
        },
        "vin": vin
    }
    req = urllib.request.Request(
        KIA_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))

    if result.get("status") != 200 or not result.get("data"):
        raise RuntimeError(f"Ungültige Antwort von Kia API: {result.get('message', 'Keine Daten für diese VIN gefunden')}")

    car_data = result["data"][0]
    sw_info_list = car_data.get("swInfo", [])
    primary_sw = sw_info_list[0] if sw_info_list else {}

    raw_post_date = primary_sw.get("postDate", "")
    noti_enc = primary_sw.get("notiNoEnc") or car_data.get("usrSwNotiNoEnc") or ""
    notice_url = f"{KIA_NOTICE_BASE_URL}/{noti_enc}" if noti_enc else "https://update.kia.com/EU/DE/search"

    return {
        "vin": car_data.get("vin", vin),
        "vehicle_name": car_data.get("vehlNm", "Kia"),
        "generation_name": car_data.get("genNm", ""),
        "platform_name": primary_sw.get("pfmNm", "Infotainment"),
        "post_date_raw": raw_post_date,
        "post_date_tuple": parse_version_tuple(raw_post_date),
        "post_date_formatted": format_month_year(parse_version_tuple(raw_post_date)),
        "sw_versions": primary_sw.get("swVer", []),
        "notice_url": notice_url,
        "checked_at": datetime.now().isoformat()
    }


def build_update_message(info, installed_ver_str):
    """Erstellt den formatierten Markdown-Text für Telegram."""
    sw_vers_str = "\n".join([f"• `{v}`" for v in info['sw_versions'][:4]])
    
    msg = (
        f"🚗 *Neues Kia Software-Update verfügbar!*\n\n"
        f"Für Ihren *{info['vehicle_name']}* steht ein neues Infotainment- & Navigations-Update bereit:\n\n"
        f"• *Fahrzeug:* {info['vehicle_name']} ({info['generation_name']})\n"
        f"• *FIN (VIN):* `{info['vin']}`\n"
        f"• *System:* {info['platform_name']}\n"
        f"• *Bisher installiert:* Veröffentlichungsmonat {installed_ver_str}\n"
        f"• *Neue Version:* *Veröffentlichungsmonat {info['post_date_formatted']}*\n"
    )

    if info['sw_versions']:
        msg += f"\n*Software-Builds:*\n{sw_vers_str}\n"

    msg += (
        f"\n📄 *Changelog & Details:*\n"
        f"[Offizielle Kia Update-Mitteilung öffnen]({info['notice_url']})\n\n"
        f"💾 *Download:*\n"
        f"Über den offiziellen [Kia Navigation Updater]({KIA_UPDATER_DOWNLOAD_URL}) herunterladen oder im Fahrzeug via OTA prüfen."
    )
    return msg


def run_check(config, force_notify=False, verbose=True):
    """Führt die Update-Prüfung durch."""
    state = load_state()
    
    # Installierte Version ermitteln: Entweder aus Config oder State
    installed_ver_str = state.get("installed_version") or config.get("installed_version", "2026.07")
    installed_tuple = parse_version_tuple(installed_ver_str)

    if verbose:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Prüfe Kia Update für VIN {config['vin']}...")
        print(f"Installierte Version laut Konfiguration: {format_month_year(installed_tuple)} ({installed_ver_str})")

    info = fetch_kia_update_info(config)
    latest_tuple = info["post_date_tuple"]

    state["installed_version"] = installed_ver_str
    state["last_checked"] = datetime.now().isoformat()
    state["latest_data"] = info

    is_newer = latest_tuple > installed_tuple
    already_notified = (state.get("last_notified_version") == info["post_date_raw"])

    if verbose:
        print(f"Aktuell online verfügbar: Veröffentlichungsmonat {info['post_date_formatted']} ({info['post_date_raw']})")
        if info['sw_versions']:
            print(f"Software-Versionen online: {', '.join(info['sw_versions'])}")

    if force_notify:
        print("Sende Telegram-Benachrichtigung (force-notify)...")
        msg = build_update_message(info, format_month_year(installed_tuple))
        success = send_telegram(config["bot_token"], config["chat_id"], msg)
        if success:
            print("✅ Telegram-Benachrichtigung erfolgreich versendet!")
            state["last_notified_version"] = info["post_date_raw"]
        else:
            print("❌ Fehler beim Senden der Telegram-Benachrichtigung.")
    elif is_newer:
        if not already_notified:
            print(f"🎉 NEUES UPDATE GEFUNDEN! ({info['post_date_formatted']} > {format_month_year(installed_tuple)})")
            msg = build_update_message(info, format_month_year(installed_tuple))
            success = send_telegram(config["bot_token"], config["chat_id"], msg)
            if success:
                print("✅ Telegram-Benachrichtigung versendet.")
                state["last_notified_version"] = info["post_date_raw"]
            else:
                print("❌ Fehler beim Senden der Benachrichtigung.")
        else:
            if verbose:
                print(f"Neues Update ({info['post_date_formatted']}) wurde bereits zuvor per Telegram gemeldet.")
    else:
        if verbose:
            print(f"Fahrzeug-Software ist auf dem neuesten Stand ({format_month_year(installed_tuple)}). Kein Update erforderlich.")

    save_state(state)
    return is_newer


def main():
    parser = argparse.ArgumentParser(
        description="Kia Update Checker: Prüft auf neue Navigation- & Infotainment-Updates für Kia-Fahrzeuge."
    )
    parser.add_argument("--vin", type=str, help="Fahrzeug-Identifizierungsnummer (VIN / FIN)")
    parser.add_argument("--installed", type=str, help="Installierte Version (z. B. '07.2026' oder '2026.07')")
    parser.add_argument("--token", type=str, help="Telegram Bot API Token")
    parser.add_argument("--chat-id", type=str, help="Telegram Chat ID")
    parser.add_argument("--env-file", type=str, default=DEFAULT_ENV_FILE, help="Pfad zu einer alternativen .env-Datei")
    
    parser.add_argument("--check", action="store_true", help="Führt die Prüfung durch (Standardmodus)")
    parser.add_argument("--status", action="store_true", help="Zeigt Status und online verfügbare Version in der Konsole an")
    parser.add_argument("--force-notify", action="store_true", help="Erzwingt das Senden einer Benachrichtigung für die aktuelle Online-Version")
    parser.add_argument("--test-telegram", action="store_true", help="Sendet eine Testnachricht an Telegram")
    parser.add_argument("--set-installed", type=str, metavar="VERSION", help="Speichert eine neu installierte Version im State (z. B. '08.2026')")

    args = parser.parse_args()
    env_vars = load_env_file(args.env_file)
    config = get_config(args, env_vars)

    if args.set_installed:
        state = load_state()
        state["installed_version"] = args.set_installed
        save_state(state)
        print(f"Installierte Version auf '{args.set_installed}' aktualisiert.")
        return

    if args.test_telegram:
        print("Sende Test-Nachricht via Telegram...")
        test_msg = (
            "🔔 *Kia Update Checker - Testnachricht*\n\n"
            "Die Telegram-Benachrichtigung funktioniert einwandfrei! Sobald Kia ein neues Update veröffentlicht, "
            "wird hier automatisch eine Info gesendet."
        )
        if send_telegram(config["bot_token"], config["chat_id"], test_msg):
            print("✅ Testnachricht erfolgreich gesendet!")
        else:
            print("❌ Fehler beim Senden der Testnachricht. Bitte Token und Chat-ID prüfen.")
        return

    if args.status:
        state = load_state()
        inst_ver = state.get("installed_version") or config.get("installed_version")
        inst_tuple = parse_version_tuple(inst_ver)
        print("=== KIA UPDATE STATUS ===")
        print(f"VIN: {config.get('vin') or 'Nicht konfiguriert'}")
        print(f"Installierte Version: {format_month_year(inst_tuple)} ({inst_ver})")
        print(f"Zuletzt benachrichtigt: {state.get('last_notified_version')}")
        print(f"Letzte Prüfung: {state.get('last_checked')}")
        if not config.get("vin"):
            print("⚠️ Keine VIN konfiguriert. Bitte --vin angeben oder in .env setzen.")
            return
        try:
            info = fetch_kia_update_info(config)
            latest_tuple = info["post_date_tuple"]
            print(f"Verfügbar auf update.kia.com: {info['post_date_formatted']} ({info['post_date_raw']})")
            print(f"Fahrzeug: {info['vehicle_name']} ({info['generation_name']})")
            if info['sw_versions']:
                print(f"Software-Builds: {', '.join(info['sw_versions'])}")
            print(f"Changelog-Link: {info['notice_url']}")
            if latest_tuple > inst_tuple:
                print("Status: ⚠️ NEUES UPDATE VERFÜGBAR")
            else:
                print("Status: 🟢 Aktuell (Kein neues Update)")
        except Exception as e:
            print(f"Fehler beim Abruf von Kia: {e}")
        return

    # Standardaktion
    if not config.get("vin"):
        print("[FEHLER] Keine VIN angegeben! Bitte über Parameter --vin, Umgebungsvariable KIA_VIN oder in .env definieren.", file=sys.stderr)
        sys.exit(1)

    run_check(config, force_notify=args.force_notify, verbose=True)


if __name__ == "__main__":
    main()
