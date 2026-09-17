# Kohortlistene

To lister med organisasjonsnumre, én per linje, sortert stigende som ni-sifrede strenger. Ingenting annet på foretaksnivå publiseres.

| Fil | Antall | Definisjon |
|---|---|---|
| `konkurs-5165.txt` | 5 165 | Konkursbo etter AS/ASA med første kunngjorte konkursåpning 1. september 2023 – 31. desember 2024 (studiens kapittel 11) |
| `tvangsavvikling-2571.txt` | 2 571 | Første kunngjorte «Tvangsoppløsning» eller «Tvangsavvikling» per foretak i samme vindu (Del II, kapittel 17; talljournalen J1) |

3 foretak står i begge listene: tvangsavviklingsvedtak og senere konkursåpning i vinduet. Studien behandler dem som beskrevet i talljournalen J1.

## Fingeravtrykk

Oppskriften er studiens egen (`del-1-hovedstudien/metodegrunnlag.json`): SHA-256 over organisasjonsnumrene som ni-sifrede strenger, sortert leksikografisk stigende, sammenføyd med komma uten mellomrom, UTF-8, uten avsluttende linjeskift.

| Kohort | SHA-256 |
|---|---|
| Konkurs, 5 165 | `a5aea019c8157dca67e09580f154860f0b10419cff1ec79906a09f7edcc07452` (identisk med det publiserte fingeravtrykket) |
| Tvangsavvikling, 2 571 | `71af2cbb64c8f6c986d2733849eef566bd0603f1cececf99bfb700945b28393b` |

Kontroll fra kommandolinjen:

```bash
python -c "import hashlib,sys;print(hashlib.sha256(','.join(sorted(l.strip() for l in open(sys.argv[1]) if l.strip())).encode()).hexdigest())" konkurs-5165.txt
```

## Om publiseringen

Studiens metodegrunnlag fra 30. august 2026 sa at ingen foretaksliste skulle publiseres, bare fingeravtrykket. Den beslutningen ble omgjort 17. september 2026 for å gjøre etterprøving direkte: en som bygger kohorten selv fra Brønnøysundregistrenes kunngjøringer, kan nå sammenlikne foretak for foretak, ikke bare hash mot hash. Listene inneholder identifikatorer for foretak (juridiske personer) hentet fra offentlige kunngjøringer, ingen regnskapstall og ingen personopplysninger.

*English:* organisation numbers for the two cohorts, one per line, sorted. The SHA-256 recipe and both fingerprints are above; the bankruptcy fingerprint equals the one published in the study. Nothing else at company level is published.
