# Mobilità in tempo reale – Reggio Emilia

Mappa web della mobilità sul territorio di Reggio Emilia:

- **traffico in tempo reale** (velocità sulle strade, aggiornata ogni 5 minuti) e **incidenti, cantieri e chiusure**, da TomTom;
- **rete del trasporto pubblico SETA**: percorsi delle linee con i colori ufficiali e fermate, con le linee che servono ogni fermata e il collegamento ai passaggi in tempo reale su [wimb.setaweb.it](https://wimb.setaweb.it).

È una pagina statica (HTML + JavaScript, libreria [Leaflet](https://leafletjs.com/)): non serve un server, basta GitHub Pages.

## Struttura

```
index.html              la mappa
config.js               configurazione (chiave TomTom)
data/seta.js            linee e fermate SETA, generate dal feed GTFS
scripts/build_seta.py   script per rigenerare data/seta.js quando cambia l'orario
.nojekyll               dice a GitHub Pages di pubblicare i file così come sono
```

## Pubblicazione su GitHub Pages

1. Crea un nuovo repository su GitHub (es. `mappa-mobilita-reggio`), pubblico.
2. Carica tutti i file di questa cartella: dalla pagina del repository, *Add file → Upload files*, trascina il contenuto della cartella e conferma con *Commit changes*.
3. Vai in *Settings → Pages*. In *Build and deployment* scegli *Deploy from a branch*, branch `main`, cartella `/ (root)`, e salva.
4. Dopo uno o due minuti la mappa è online su `https://<tuo-utente>.github.io/mappa-mobilita-reggio/`.

## Chiave TomTom

La chiave gratuita si crea su [developer.tomtom.com](https://developer.tomtom.com/) (piano gratuito senza carta di credito; servono Traffic API e Map Display API).

Due modi di usarla:

- **Chiave nella pagina (consigliato per una mappa pubblica).** Nel portale TomTom apri la chiave, attiva la *Domain whitelist* e aggiungi `<tuo-utente>.github.io`. Poi scrivi la chiave in `config.js`:
  ```js
  window.MAPPA_CONFIG = { tomtomKey: 'LA_TUA_CHIAVE' };
  ```
  Il campo per la chiave sparisce e la mappa parte da sola. Senza whitelist la chiave, visibile nel codice, potrebbe essere usata da altri siti e consumare la quota.
- **Chiave inserita da chi visita.** Lascia `tomtomKey: ''`: ogni visitatore incolla la propria chiave nel pannello, che resta salvata solo nel suo browser.

Il piano gratuito include 200.000 tile al mese per il traffico; le tile della mappa di sfondo contano su una quota separata (Map Display API). Il consumo si controlla dal portale TomTom.

## Aggiornare gli orari SETA

Il feed attuale è valido dal 03/11/2026 al 23/12/2026. Quando esce un nuovo orario:

1. Scarica il nuovo file `.zip` dalla pagina del feed su [Mobility Database](https://mobilitydatabase.org/feeds/gtfs/mdb-3557) (pulsante *Download*).
2. Dalla cartella del progetto esegui (serve Python 3, nessuna libreria aggiuntiva):
   ```
   python3 scripts/build_seta.py percorso/del/feed.zip data/seta.js
   ```
3. Carica su GitHub il nuovo `data/seta.js`.

## Fonti e licenze

- **Traffico e mappa di sfondo:** © TomTom, secondo i [termini d'uso TomTom](https://developer.tomtom.com/terms-and-conditions).
- **Mappa di sfondo senza chiave:** © contributori [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL).
- **Trasporto pubblico:** orari SETA S.p.A., convertiti in GTFS da BusOne ([condizioni d'uso](https://proxy.busone.app/seta-re/readme)). L'uso gratuito è consentito a privati ed enti non profit; per altri enti, compresa la pubblicazione da parte di una pubblica amministrazione, serve il consenso scritto di BusOne (info@busone.app). In alternativa si possono usare gli orari ufficiali pubblicati sul National Access Point (CCISS) in formato NeTEx.
- **Libreria cartografica:** [Leaflet](https://leafletjs.com/) (BSD-2-Clause).
