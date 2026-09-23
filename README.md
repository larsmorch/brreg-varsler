# Brønnøysundregistrene - Automatisk Regnskapsovervåker

Et automatisert Python-skript som overvåker utvalgte norske bedrifter for nye årsregnskap via Brønnøysundregistrene sine åpne API-er. Skriptet kjører automatisk via GitHub Actions, sporer publiserte regnskapsår ved hjelp av en lokal state-fil, og sender e-postvarsler ved nye regnskap eller eventuelle driftsfeil.

## Funksjonalitet
- **Automatisk overvåking:** Sjekker en definert liste med organisasjonsnumre mot Regnskapsregisteret og Enhetsregisteret.
- **Navneoppslag:** Henter automatisk offisielle selskapsnavn for ryddigere varsler.
- **Persistens:** Lagrer sist sjekkede regnskapsår i `siste_regnskap.json` slik at du kun får varsel én gang per nye regnskap.
- **Feilvarsling:** Sender e-post hvis API-et er nede (f.eks. ved 503-feil) eller om andre nettverksfeil oppstår.
- **Skybasert kjøring:** Kjører helt automatisk daglig via GitHub Actions uten behov for en påslått lokal PC.

---

## Prosjektstruktur
```text
├── .github/
│   └── workflows/
│       └── brreg_sjekk.yml   # GitHub Actions workflow for automatiske kjøringer
├── script.py                 # Hovedskript for henting, sjekk og e-postvarsling
├── siste_regnskap.json       # Vedlikeholdt fil som holder styr på sist kjente regnskapsår
└── README.md

---
# Slik kommer du i gang
1. Klon eller opprett prosjektet
Sørg for at du har script.py og mappen .github/workflows/brreg_sjekk.yml i repository-et ditt.

2. Sett opp GitHub Secrets
For at e-postvarslingen skal fungere i skyen, må du legge til app-passordet ditt som en hemmelighet i GitHub:

Gå til ditt repository på GitHub.

Velg Settings > Secrets and variables > Actions.

Klikk på New repository secret.

Gi den navnet EPOST_PASSORD og lim inn ditt genererte e-post-passord (f.eks. Gmail App Password).

3. Konfigurer bedriftene du vil overvåke
Åpne script.py og rediger FIRMAER-listen øverst i filen med organisasjonsnumrene du ønsker å følge med på:

Python
FIRMAER = [
    "12345678", # Eksempel AS
    "87654321", # Eksempel 2 AS
]
Kjøring
Manuell kjøring
Du kan når som helst kjøre skriptet manuelt fra GitHub:

Gå til Actions-fanen i repository-et ditt.

Velg workflowen Sjekk Brønnøysundregistrene i venstre meny.

Klikk på Run workflow.

Automatisk kjøring
Skriptet er satt opp til å kjøre automatisk i henhold til tidsplanen definert i brreg_sjekk.yml (satt opp til å kjøre daglig).
