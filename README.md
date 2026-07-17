# Downloader MVP

Lokalni webova aplikace v Pythonu postavena na NiceGUI. Slouzi jako jednoduchy frontend pro JDownloader 2 bez vlastniho web UI v JD2. Komunikace probiha primo na lokalni HTTP API JDownloaderu 2, bez My.JDownloader a bez auth vrstvy v aplikaci.

## Co MVP umi

- vlozit jeden nebo vice odkazu do multiline pole,
- nabidnout existujici cilove slozky pod konfigurovanym rootem do hloubky max. 2 urovni,
- nabidnout pevnou defaultni slozku z konfigurace,
- pri detekci serialu pres `guessit` automaticky pridat podslozku `Season XX`,
- vytvorit cilovou slozku na disku jeste pred odeslanim do JD2,
- zobrazit aktivni, cekajici a od startu aplikace i dokoncene polozky s progress barem.

## Architektura

Projekt je rozdeleny tak, aby sel pozdeji snadno rozsirit treba o scraping modul:

- `app/config.py`: nacteni `.env` a `config.yaml`
- `app/services/jd_client.py`: klient pro lokalni JD2 HTTP API
- `app/services/folder_service.py`: scan a validace slozek pod rootem
- `app/services/parser_service.py`: rozpoznani serialu pres `guessit`
- `app/services/submission_service.py`: rozdeleni linku podle cile a odeslani do JD2
- `app/services/queue_service.py`: polling fronty a in-memory completed polozky
- `app/ui/pages.py`: NiceGUI stranka

## Pozadavky

- Python 3.11 nebo novejsi
- JDownloader 2
- zapnute lokalni direct API JD2 na stejne masine nebo dostupne pres VPN/LAN

## Instalace aplikace

### Windows

1. Nainstaluj Python 3.11+.
2. Otevri PowerShell v adresari projektu.
3. Vytvor a aktivuj virtualni prostredi:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Nainstaluj aplikaci:

```powershell
python -m pip install --upgrade pip
pip install -e .
```

5. Priprav konfiguraci:

```powershell
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

6. Uprav `config.yaml`. `.env` je momentalne volitelny a slouzi jen pro lokalni override promennych.
7. Spust aplikaci:

```powershell
python -m app
```

8. Otevri `http://127.0.0.1:8080`.

### Linux / Ubuntu

1. Nainstaluj Python 3.11+, `python3-venv` a `pip`.
2. V adresari projektu spust:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
cp .env.example .env
cp config.example.yaml config.yaml
```

3. Uprav `config.yaml`.
4. Spust aplikaci:

```bash
python -m app
```

## Konfigurace

### `config.yaml`

```yaml
download_root: ./downloads
default_target: incoming
queue_refresh_seconds: 5
app_host: 127.0.0.1
app_port: 8080
jd_base_url: http://127.0.0.1:3129
jd_request_timeout_seconds: 15
```

### Volitelne `.env`

`.env` uz neni potreba pro JD2 auth. Muzes ho nechat prazdny, nebo pouzit jen pro local override:

```dotenv
JD_BASE_URL=http://127.0.0.1:3129
JD_REQUEST_TIMEOUT_SECONDS=15
```

### Vyznam nastaveni

- `download_root`: root adresar, pod kterym aplikace skenuje existujici slozky
- `default_target`: pevna relativni cesta pod rootem, nabidne se jako `Default (...)`
- `queue_refresh_seconds`: interval obnovy fronty
- `app_host`, `app_port`: bind NiceGUI serveru
- `jd_base_url`: base URL lokalniho JD2 API
- `jd_request_timeout_seconds`: timeout HTTP volani na JD2 API

`default_target` i vsechny rucne vybirane cile musi byt maximalne 2 urovne pod `download_root`.

## Setup JDownloader 2

### Co aplikace od JD2 potrebuje

Aplikace pocita s tim, ze JD2 bezi lokalne a ma zapnute lokalni direct API. Nepouziva My.JDownloader ucet ani `myjdapi`.

Oficialni My.JDownloader developer docs uvadi, ze direct/deprecated API lze pouzit k obejiti jejich serveru:
https://my.jdownloader.org/developers/index.html

Support clanek zaroven potvrzuje, ze My.JDownloader ucet je volitelny:
https://support.jdownloader.org/fr/knowledgebase/article/what-is-myjdownloader

### Windows

1. Nainstaluj a spust JDownloader 2.
2. Otevri `Settings`.
3. Prejdi do `Advanced Settings`.
4. Vyhledej `Deprecated API` nebo `Remote API`.
5. Zapni deprecated/direct API tak, aby bezelo lokalne.
6. Pokud je k dispozici bind/host/port nastaveni, nech API na `127.0.0.1` a nastav port, ktery das do `jd_base_url`.
7. Otestuj, ze endpoint odpovida:

```powershell
Invoke-WebRequest http://127.0.0.1:3129/jdcheckjson
```

### Ubuntu / Linux headless

1. Nainstaluj Java runtime.
2. Vytvor adresar pro JD2, stahni `JDownloader.jar` a spust prvni inicializaci.
3. Pokud server nema GUI, pouzij `xvfb-run` nebo systemd sluzbu.
4. V JD2 zapni deprecated/direct API v `Advanced Settings`.
5. Pokud to JD2 dovoluje, nech API bindnute jen na `127.0.0.1`.
6. Zkontroluj odpoved endpointu:

```bash
curl http://127.0.0.1:3129/jdcheckjson
```

Jednorazovy start:

```bash
mkdir -p ~/JDownloader
cd ~/JDownloader
wget http://installer.jdownloader.org/JDownloader.jar
xvfb-run -a java -Djava.awt.headless=false -jar JDownloader.jar
```

Priklad jednoduche systemd user sluzby:

```ini
[Unit]
Description=JDownloader 2 Headless
After=network-online.target

[Service]
WorkingDirectory=%h/JDownloader
ExecStart=/usr/bin/xvfb-run -a /usr/bin/java -Djava.awt.headless=false -jar %h/JDownloader/JDownloader.jar
Restart=always

[Install]
WantedBy=default.target
```

Po vytvoreni sluzby:

```bash
systemctl --user daemon-reload
systemctl --user enable --now jdownloader.service
```

Poznamka: nektere pluginy a captchy mohou i tak vyzadovat obcasny pristup k plnemu GUI.

## No-auth a auth varianta

### No-auth varianta

Tohle je jedina varianta, kterou aplikace primo podporuje:

- JD2 API bezi lokalne, typicky `http://127.0.0.1:3129`
- aplikace vola API primo bez prihlaseni
- bezpecnost resis sitove, typicky tim, ze API neotevres do internetu a pristup zvenci resis pres VPN

### Auth varianta

Aplikace zadnou auth vrstvu k JD2 API neimplementuje a neposila zadne username/password.

Pokud nekdy budes chtit auth, res ji mimo aplikaci:

- VPN
- firewall pravidla
- reverzni proxy pred API

## Jak aplikace pracuje se slozkami

1. Nacte `download_root`.
2. Projde fyzicky existujici adresare do hloubky 2:
   - `root/movies`
   - `root/serialy/Futurama`
3. Hlubsi adresare nenabidne v dropdownu.
4. Tlacitko s ikonou reload provede rescan bez restartu aplikace.
5. Pokud `guessit` rozpozna serial, aplikace prida `Season XX` a cilovou slozku vytvori.

Priklad:

- vybrany cil: `serialy/Futurama`
- link: `https://example.com/Futurama.S01E03.1080p.mkv`
- finalni cil: `serialy/Futurama/Season 01`

## Spusteni testu

```bash
pytest
```

## Omezeni MVP

- integrace je psana pro lokalni direct/deprecated JD2 API bez auth vrstvy,
- completed polozky se drzi jen v pameti od spusteni NiceGUI procesu,
- UI zatim pracuje s jednou hlavni strankou,
- robustnost queue mapovani zavisi na datech vracenych konkretni verzi JD2 API,
- JD2 muze prepsat cilovou slozku vlastnimi Packagizer pravidly; aplikace proto posila `overwritePackagizerRules=True`, ale je vhodne mit Packagizer v JD2 pod kontrolou.

## Doporuceni pro dalsi krok

- pridat persistentni historii submitu,
- pridat stranku pro editaci konfigurace,
- doplnit scraping modul jako samostatnou service/UI sekci,
- rozsirit queue pohled o package-level agregaci a filtrovani.
