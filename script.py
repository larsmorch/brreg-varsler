import requests
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
import time
import hashlib
from datetime import datetime

# --- KONFIGURASJON ---
org_env = os.environ.get("ORG_LISTE")
if org_env:
    FIRMAER = eval(org_env)
else:
    # Lokal fallback-liste for testing på egen PC
    FIRMAER = [
        "984669151",  # ODL
        "923609016",  # EQUINOR
    ]

STATE_FILE = "siste_regnskap.json"

# E-post innstillinger
AVSENDER_EPOST = os.environ.get("AVSENDER_EPOST", "din.epost@gmail.com")
MOTTAKER_EPOST = os.environ.get("MOTTAKER_EPOST", "din.epost@gmail.com")
EPOST_PASSORD = os.environ.get("EPOST_PASSORD")


def hash_orgnr(orgnr):
    """Omgjør organisasjonsnummeret til en sikker SHA-256-hash."""
    return hashlib.sha256(str(orgnr).strip().encode("utf-8")).hexdigest()


def last_inn_state():
    """
    Leser state-filen.

    Støtter både:
    - Gammel struktur: { "hash": 2024 }
    - Ny struktur: { "regnskap": {...}, "kjoringer": [...] }
    """
    tom_state = {
        "regnskap": {},
        "kjoringer": []
    }

    if not os.path.exists(STATE_FILE):
        return tom_state

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return tom_state

        # Ny filstruktur
        if "regnskap" in data and "kjoringer" in data:
            return {
                "regnskap": data.get("regnskap", {}),
                "kjoringer": data.get("kjoringer", [])
            }

        # Migrer automatisk fra gammel filstruktur
        return {
            "regnskap": data,
            "kjoringer": []
        }

    except (json.JSONDecodeError, OSError) as e:
        print(f"Kunne ikke lese state-fil: {e}")
        return tom_state


def lagre_state(state):
    """Lagrer både regnskapsstatus og kjørehistorikk."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)


def registrer_kjoring(state, suksess):
    """Legger til resultatet av den aktuelle kjøringen i historikken."""
    state["kjoringer"].append({
        "tidspunkt": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "suksess": suksess
    })


def send_epost(emne, innhold):
    """Sender en e-post via Gmails SMTP-server."""
    if not EPOST_PASSORD:
        print("Varsel: EPOST_PASSORD er ikke satt i miljøvariablene. E-post sendes ikke.")
        return

    msg = EmailMessage()
    msg.set_content(innhold)
    msg["Subject"] = emne
    msg["From"] = AVSENDER_EPOST
    msg["To"] = MOTTAKER_EPOST

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(AVSENDER_EPOST, EPOST_PASSORD)
            server.send_message(msg)
        print("E-postvarsel sendt med suksess!")
    except Exception as e:
        print(f"Feil ved sending av e-post: {e}")


def sjekk_flere_regnskap():
    headers = {"Accept": "application/json"}
    state = last_inn_state()
    lagrede_data = state["regnskap"]

    feil_meldinger = []
    nye_regnskap_meldinger = []

    # Denne verdien brukes i finally-blokken dersom en uventet feil oppstår.
    suksess = False

    try:
        for orgnr in FIRMAER:
            # Generer hash av organisasjonsnummeret for bruk i state-filen
            org_hash = hash_orgnr(orgnr)

            # 1. Hent bedriftsnavn fra Enhetsregisteret
            enhet_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}"
            bedriftsnavn = f"Org.nr {orgnr}"

            try:
                enhet_resp = requests.get(enhet_url, headers=headers, timeout=30)
                if enhet_resp.status_code == 200:
                    bedriftsnavn = enhet_resp.json().get("navn", bedriftsnavn)
            except requests.exceptions.RequestException:
                pass

            # 2. Hent regnskapsdata
            api_url = f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"

            try:
                # Vent 2 sekunder mellom hver forespørsel for å skåne serveren
                time.sleep(2)

                response = requests.get(api_url, headers=headers, timeout=30)

                if response.status_code == 404:
                    print(f"[{bedriftsnavn}] Fant ingen regnskap i registeret (404).")
                    continue

                if response.status_code == 503:
                    feil_melding = (
                        f"[{bedriftsnavn}] Brønnøysundregistrene er utilgjengelige "
                        "(503 Service Unavailable)."
                    )
                    print(feil_melding)
                    feil_meldinger.append(feil_melding)
                    continue

                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    registrerte_aar = [
                        int(item["regnskapsperiode"]["tilDato"][:4])
                        for item in data
                        if "regnskapsperiode" in item
                        and "tilDato" in item["regnskapsperiode"]
                    ]
                else:
                    print(f"[{bedriftsnavn}] Uventet responsformat fra API-et.")
                    continue

                if not registrerte_aar:
                    print(f"[{bedriftsnavn}] Klarte ikke å lese ut årstall fra regnskapsperioden.")
                    continue

                nyeste_aar = max(registrerte_aar)
                siste_kjente_aar = lagrede_data.get(org_hash, 0)

                if nyeste_aar > siste_kjente_aar:
                    melding = f"{bedriftsnavn} ({orgnr}) har publisert regnskap for år {nyeste_aar}."
                    print(f"🚨 NYTT REGNSKAP: {melding}")

                    nye_regnskap_meldinger.append(melding)
                    lagrede_data[org_hash] = nyeste_aar
                else:
                    print(f"[{bedriftsnavn}] Ingen nye regnskap. Nyeste er {nyeste_aar}.")

            except requests.exceptions.RequestException as e:
                feil_melding = f"[{bedriftsnavn}] Feil ved henting av data: {e}"
                print(feil_melding)
                feil_meldinger.append(feil_melding)

        # Send e-post hvis det enten er nye regnskap eller feilmeldinger
        if nye_regnskap_meldinger or feil_meldinger:
            emne = []
            innhold_deler = []

            if nye_regnskap_meldinger:
                emne.append("Nye årsregnskap tilgjengelig!")
                innhold_deler.append(
                    "Følgende bedrifter har levert nye årsregnskap:\n\n"
                    + "\n".join(nye_regnskap_meldinger)
                )

            if feil_meldinger:
                emne.append("Feil ved henting av regnskap")
                innhold_deler.append(
                    "Følgende feil oppstod under sjekken:\n\n"
                    + "\n".join(feil_meldinger)
                )

            send_epost(
                "Varsel: " + " og ".join(emne),
                "\n\n--------------------\n\n".join(innhold_deler)
            )
        else:
            print("Ingen nye endringer eller feil å melde.")

        # Kjøringen er vellykket dersom det ikke var noen hente-feil.
        suksess = len(feil_meldinger) == 0

    except Exception as e:
        print(f"Uventet feil i skriptet: {e}")
        suksess = False

    finally:
        # Dette skjer alltid, også ved uventede feil.
        registrer_kjoring(state, suksess)
        lagre_state(state)

        status = "vellykket" if suksess else "mislykket"
        print(f"Kjøring registrert som {status} i {STATE_FILE}.")


if __name__ == "__main__":
    sjekk_flere_regnskap()
