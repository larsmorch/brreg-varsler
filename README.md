# Brønnøysundregistrene - Automatisk Regnskapsovervåker

Et automatisert Python-skript som overvåker utvalgte norske bedrifter for nye årsregnskap via Brønnøysundregistrene sine åpne API-er. Skriptet kjører automatisk via GitHub Actions, sporer publiserte regnskapsår ved hjelp av en hashet state-fil for økt personvern, og sender e-postvarsler ved nye regnskap eller eventuelle driftsfeil.

## Funksjonalitet
- **Automatisk overvåking:** Sjekker en definert liste med organisasjonsnumre mot Regnskapsregisteret og Enhetsregisteret.
- **Navneoppslag:** Henter automatisk offisielle selskapsnavn for ryddigere varsler.
- **Hashet Persistens:** Lagrer sist sjekkede regnskapsår i `siste_regnskap.json` ved hjelp av SHA-256-hashede organisasjonsnumre, slik at filen forblir anonymisert selv i et offentlig repo.
- **Feilvarsling:** Sender e-post hvis API-et er nede (f.eks. ved 503-feil) eller om andre nettverksfeil oppstår.
- **Skybasert kjøring:** Kjører helt automatisk daglig via GitHub Actions.

---

## Prosjektstruktur
```text
├── .github/
│   └── workflows/
│       └── brreg_sjekk.yml   # GitHub Actions workflow for automatiske kjøringer
├── script.py                 # Hovedskript for henting, sjekk og e-postvarsling
├── siste_regnskap.json       # Anonymisert state-fil (genereres automatisk)
└── README.md
```

Slik kommer du i gang
1. Klon eller opprett prosjektet
Sørg for at du har script.py og mappen .github/workflows/brreg_sjekk.yml i repository-et ditt.

2. Sett opp GitHub Secrets
For at skriptet skal fungere i skyen, må du legge til nødvendige hemmeligheter under Settings > Secrets and variables > Actions i repository-et ditt:

EPOST_PASSORD: Ditt genererte app-passord for e-post (f.eks. Gmail App Password).

MIN_EPOST: E-postadressen som skal brukes som både avsender og mottaker for varsler.

ORG_LISTE: Listen over organisasjonsnumre du vil overvåke. Denne kan struktureres som en ekte Python-liste med kommentarer, akkurat slik:

[
    "911958821", # Eksempel AS 1
    "989235699", # Eksempel AS 2
]

3. Konfigurer workflow-miljøvariabler
Sørg for at brreg_sjekk.yml-filen din sender med disse hemmelighetene som miljøvariabler under kjøringen av script.py:

YAML
      - name: Kjør Python-script
        env:
          EPOST_PASSORD: ${{ secrets.EPOST_PASSORD }}
          MOTTAKER_EPOST: ${{ secrets.MIN_EPOST }}
          AVSENDER_EPOST: ${{ secrets.MIN_EPOST }}
          ORG_LISTE: ${{ secrets.ORG_LISTE }}
        run: python script.py
Kjøring
Manuell kjøring
Du kan når som helst kjøre skriptet manuelt fra GitHub:

Gå til Actions-fanen i repository-et ditt.

Velg workflowen Sjekk Brønnøysundregistrene i venstre meny.

Klikk på Run workflow.

Automatisk kjøring
Skriptet er satt opp til å kjøre automatisk i henhold til tidsplanen definert i brreg_sjekk.yml.
