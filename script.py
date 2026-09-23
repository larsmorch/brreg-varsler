import requests
import json
import os
import smtplib
import ssl
from email.message import EmailMessage

# --- KONFIGURASJON ---
FIRMAER = [
    "911958821", # WG
    "989235699", # Managua
]

STATE_FILE = "siste_regnskap.json"

# E-post innstillinger (Husk å fylle inn dine egne)
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

    for orgnr in FIRMAER:
        api_url = f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}"
        
        try:
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 404:
                print(f"[{orgnr}] Fant ingen regnskap i registeret (404).")
                continue
                
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                # Trekker ut de 4 første tegnene (årstallet) fra "tilDato" 
                registrerte_aar = [
                    int(item["regnskapsperiode"]["tilDato"][:4]) 
                    for item in data 
                    if "regnskapsperiode" in item and "tilDato" in item["regnskapsperiode"]
                ]
            else:
                continue

            if not registrerte_aar:
                print(f"[{orgnr}] Klarte ikke å lese ut årstall fra regnskapsperioden.")
                continue

            nyeste_aar = max(registrerte_aar)
            siste_kjente_aar = lagrede_data.get(orgnr, 0)

            if nyeste_aar > siste_kjente_aar:
                melding = f"Org.nr {orgnr} har publisert regnskap for år {nyeste_aar}."
                print(f"🚨 NYTT REGNSKAP: {melding}")
                
                nye_regnskap_meldinger.append(melding)
                lagrede_data[orgnr] = nyeste_aar
                oppdatert = True
            else:
                print(f"[{orgnr}] Ingen nye regnskap. Nyeste er {siste_kjente_aar}.")

        except requests.exceptions.RequestException as e:
            print(f"[{orgnr}] Feil ved henting av data: {e}")

    if oppdatert:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(lagrede_data, f, indent=4)
        
        if nye_regnskap_meldinger:
            emne = "Varsel: Nye årsregnskap tilgjengelig!"
            innhold = "Følgende bedrifter har levert nye årsregnskap til Brønnøysundregistrene:\n\n"
            innhold += "\n".join(nye_regnskap_meldinger)
            
            send_epost(emne, innhold)
    else:
        print("Ingen nye endringer funnet.")

if __name__ == "__main__":
    sjekk_flere_regnskap()
