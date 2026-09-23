import requests
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
import time

# --- KONFIGURASJON ---
FIRMAER = [
    "911958821", # W. Giertsen AS
    "986082506", # W. Giertsen Tunnel AS
    "914323924", # W. Giertsen Energy Solutions AS
    "918285040", # W. Giertsen Ventures AS
    "989235699", # Managua AS
    "911988844", # EMS Holding AS
    "936760589", # Det Norske Aktieselskab af 1392 AS
    "917071918", # Fias Company AS
]

STATE_FILE = "siste_regnskap.json"

# E-post innstillinger
AVSENDER_EPOST = "larmorch@gmail.com" 
MOTTAKER_EPOST = "larmorch@gmail.com"
EPOST_PASSORD = os.environ.get("EPOST_PASSORD") 

def send_epost(emne, innhold):
    """Sender en e-post via Gmails SMTP-server."""
    if not EPOST_PASSORD:
        print("Varsel: EPOST_PASSORD er ikke satt i miljøvariablene. E-post sendes ikke.")
        return

    msg = EmailMessage()
    msg.set_content(innhold)
    msg['Subject'] = emne
    msg['From'] = AVSENDER_EPOST
    msg['To'] = MOTTAKER_EPOST

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
    
    lagrede_data = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                lagrede_data = json.load(f)
            except json.JSONDecodeError:
                lagrede_data = {}

    oppdatert = False
    nye_regnskap_meldinger = [] 
    feil_meldinger = []

    for orgnr in FIRMAER:
        # 1. Hent bedriftsnavn fra Enhetsregisteret
        enhet_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}"
        bedriftsnavn = f"Org.nr {orgnr}"
        try:
            enhet_resp = requests.get(enhet_url, headers=headers)
            if enhet_resp.status_code == 200:
                bedriftsnavn = enhet_resp.json().get("navn", bedriftsnavn)
        except Exception:
            pass

        # 2. Hent regnskapsdata
        api_url = f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"
        
        try:
            # Vent 2 sekunder mellom hver forespørsel for å skåne serveren
            time.sleep(2)
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 404:
                print(f"[{bedriftsnavn}] Fant ingen regnskap i registeret (404).")
                continue
                
            if response.status_code == 503:
                feil_melding = f"[{bedriftsnavn}] Brønnøysundregistrene er utilgjengelige (503 Service Unavailable)."
                print(feil_melding)
                feil_meldinger.append(feil_melding)
                continue

            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                registrerte_aar = [
                    int(item["regnskapsperiode"]["tilDato"][:4]) 
                    for item in data 
                    if "regnskapsperiode" in item and "tilDato" in item["regnskapsperiode"]
                ]
            else:
                continue

            if not registrerte_aar:
                print(f"[{bedriftsnavn}] Klarte ikke å lese ut årstall fra regnskapsperioden.")
                continue

            nyeste_aar = max(registrerte_aar)
            siste_kjente_aar = lagrede_data.get(orgnr, 0)

            if nyeste_aar > siste_kjente_aar:
                melding = f"{bedriftsnavn} ({orgnr}) har publisert regnskap for år {nyeste_aar}."
                print(f"🚨 NYTT REGNSKAP: {melding}")
                
                nye_regnskap_meldinger.append(melding)
                lagrede_data[orgnr] = nyeste_aar
                oppdatert = True
            else:
                print(f"[{bedriftsnavn}] Ingen nye regnskap. Nyeste er {siste_kjente_aar}.")

        except requests.exceptions.RequestException as e:
            feil_melding = f"[{bedriftsnavn}] Feil ved henting av data: {e}"
            print(feil_melding)
            feil_meldinger.append(feil_melding)

    # Lagre status hvis vi fant nye regnskap
    if oppdatert:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(lagrede_data, f, indent=4)

    # Send e-post hvis det enten er nye regnskap ELLER feilmeldinger
    if nye_regnskap_meldinger or feil_meldinger:
        emne = []
        innhold_deler = []

        if nye_regnskap_meldinger:
            emne.append("Nye årsregnskap tilgjengelig!")
            innhold_deler.append("Følgende bedrifter har levert nye årsregnskap:\n\n" + "\n".join(nye_regnskap_meldinger))

        if feil_meldinger:
            emne.append("Feil ved henting av regnskap")
            innhold_deler.append("Følgende feil oppstod under sjekken:\n\n" + "\n".join(feil_meldinger))

        epost_emne = "Varsel: " + " og ".join(emne)
        epost_innhold = "\n\n--------------------\n\n".join(innhold_deler)

        send_epost(epost_emne, epost_innhold)
    else:
        print("Ingen nye endringer eller feil å melde.")

if __name__ == "__main__":
    sjekk_flere_regnskap()
