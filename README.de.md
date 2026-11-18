# GTA V Legacy

**Los Santos. San Andreas. PlayStation 2.**

Ein inoffizielles Konvertierungsprojekt, das ausgewählte **Fahrzeuge, Waffen, Audio- und Grafik-Assets aus GTA V** nach **GTA San Andreas für PlayStation 2** bringt. Ein plattformübergreifendes Python-Tool überträgt die Projektdateien auf ein kompatibles Spiel-ISO und erstellt daraus ein neues Image.

Der Build läuft mit Python unter **Windows, Linux und macOS**. UltraISO und die ursprünglichen Windows-Hilfsprogramme sind nicht erforderlich.

Das fertige Image ist für Emulatoren wie PCSX2 und PS2-Hardware mit OPL/FreeMcBoot vorgesehen. Kompatibilität und Spielbarkeit sind nicht garantiert.

> **🧪 CLOSED ALPHA** · Eine frühe, begrenzte Testphase – noch keine fertige Veröffentlichung. Funktionen und Assets können fehlen; Abstürze sind möglich.
>
> **Dieses Repository führt die Legacy von [GTAVLegacy von Daniel Santos](https://github.com/DanielSant0s/GTAVLegacy) weiter.** Siehe [Projekt-Historie](#projekt-historie).

**Aktueller Test-Build:** `GTA Legacy Alpha build 0.1.9`. Die Startsequenz verwendet die GTA-V-Clips aus `src/intro/` anstelle der San-Andreas-Intros. Sie wurde in PCSX2 geprüft; ein Test auf echter PS2-Hardware steht noch aus.

**Persönliche Notiz:** Dieses Projekt steht derzeit ganz unten auf meiner Aufgabenliste. Andere Aufgaben haben im Moment Vorrang.

[ISO bauen](#schnellstart) · [Voraussetzungen](#voraussetzungen) · [CLI-Referenz](#kommandozeile) · [Projekt-Historie](#projekt-historie) · [English](README.md)

---

<details>
<summary>📚 Inhalt</summary>

- [Projekt-Historie](#projekt-historie)
- [Was das Projekt macht](#was-das-projekt-macht)
- [Voraussetzungen](#voraussetzungen)
- [Schnellstart](#schnellstart)
- [Kommandozeile](#kommandozeile)
- [config.ini](#configini)
- [Wie der Build abläuft](#wie-der-build-abläuft)
- [Projektstruktur](#projektstruktur)
- [Sprache und Benennung](#sprache-und-benennung)
- [Assets hinzufügen](#assets-hinzufügen)
- [Audio / Radio-Streams](#audio--radio-streams)
- [Bekannte Stolperfallen](#bekannte-stolperfallen)
- [Projekt weiterführen](#projekt-weiterführen)
- [Fork veröffentlichen](#fork-veröffentlichen)
- [Hinweise für Entwickler](#hinweise-für-entwickler)
- [Rechtliches](#rechtliches)
- [Credits](#credits)

</details>

---

## 🧬 Projekt-Historie

Dieses Projekt ist keine Neuentwicklung, sondern die **Weiterführung (Legacy-Fork)** des ursprünglichen GTA-V-Legacy-Projekts:

| | |
|---|---|
| **Originalprojekt** | [DanielSant0s/GTAVLegacy](https://github.com/DanielSant0s/GTAVLegacy) |
| **Originalautor** | Daniel Santos ([@DanielSant0s](https://github.com/DanielSant0s)) |
| **Originalarbeit** | Build-System, Asset-Konvertierungen, PS2-Overlays und -Plugins, `SLUS_209.46`-Toolchain |
| **Diese Weiterführung** | [baummarder/GTAVLegacyRW](https://github.com/baummarder/GTAVLegacyRW) – Dokumentation, Python-Build, Tests, Wartung |
| **Maintainer** | [@baummarder](https://github.com/baummarder) |
| **Lizenz** | MIT für den Code (siehe `LICENSE`, © 2023 Daniel Santos) |

Die 15 ursprünglichen Commits (2023–2024) bleiben unverändert erhalten und sind weiterhin von Daniel Santos verfasst. Änderungen dieser Weiterführung kommen als zusätzliche Commits hinzu. KI-Co-Autoren werden bei Bedarf pro Commit genannt.

Wenn du auf diesem Projekt aufbaust, halte die Historie sichtbar und nenne den Originalautor.

---

## 🎮 Was das Projekt macht

`build.py` ist das zentrale Build-Tool. Ein Befehl führt alle Stages aus `buildiso.py` aus:

1. prüft, ob das Original-ISO vorhanden und unverändert ist (MD5/SHA1),
2. entpackt das ISO in den Ordner `build/`,
3. kopiert die eigenen Dateien aus `src/` über das Original,
4. entpackt die geteilten `STREAMS.7z.*`-Archive (GTA-V-Radiosender als PS2-Audio-Streams),
5. mischt die konvertierten Assets mit einem eingebauten IMG-Writer in `gta3.img` und `gta_int.img`,
6. erstellt mit den enthaltenen `mkps2iso`-PS2-DVD-Werkzeugen das fertige Image,
7. öffnet das fertige ISO erneut und prüft die wichtigsten Einträge.

Zusätzlich liegen im Repo PS2-Binärpatches (`src/overlays/*.NM`, `src/plugins/*.dep`), die das Spiel auf Konsolen-Ebene erweitern (u. a. CLEO-Support und eigene Opcodes).

### Kompatibilität auf einen Blick

| Bereich | Status | Hinweis |
|---|---|---|
| Build-Pipeline | ✅ Implementiert | Erstellt ein ISO und prüft die erforderlichen Dateien. |
| NTSC-U-v1.03-Eingabe | ✅ Akzeptiert | Build und Patches zielen auf diese Spielversion. |
| GTA-V-Startclips | ✅ Enthalten | `VLOGOS.RGM` und `VLOAD.RGM` ersetzen die San-Andreas-Startvideos; in PCSX2 geprüft. |
| PAL (`SLES_529.27`) | ⛔ Vorübergehend deaktiviert | Der PS2-Startbildschirm erscheint, aber das Spiel startet nicht weiter. Die PAL-Untersuchung liegt getrennt unter `experimental/pal/`. |
| Andere Regionen/Versionen | ⚪ Nicht unterstützt | Verwende vorerst die unterstützte US-NTSC-U-Version 1.03. |
| Kompatibilität im Spiel | ⚪ Nicht verifiziert | Ein erfolgreich erstelltes ISO bestätigt noch keine Spielbarkeit auf PCSX2 oder PS2-Hardware. |

Enthaltene Asset-Kategorien:

| Kategorie | Beispiele |
|---|---|
| Fahrzeuge | Annis Remus, Declasse Impaler/Vigero, Pfister Comet, HVY Nightshark, Imponte Ruiner 2000, Blimp |
| Waffen | AK47, M4, MP5, RPG, Desert Eagle, Messer, Schaufel |
| Peds | Alien, Barry, Chopper, Cop |
| Map / Interiors | Billboards, Munation-Interiors, Vending Machines, Underwater |
| Vegetation | Palmen, Gras |
| HUD / UI | `VLHUD.TXD`, `VHUD.TXD`, `VPHONE*.TXD`, Radar-Kacheln |
| Audio | GTA-V-Radiosender als PS2-Streams (`src/audio/STREAMS`) |

### 📸 Screenshots

Im Repository gibt es noch keine geprüften Gameplay-Screenshots des aktuellen Builds. Echte Aufnahmen kommen hinzu, sobald der Build im Spiel getestet wurde; Mockups werden nicht als Screenshots verwendet.

---

## 🧰 Voraussetzungen

| Benötigt | Details |
|---|---|
| **Python 3.9+** | Getestet mit Python 3.14 unter Windows. Aufruf über `python` (unter Linux/macOS auch `python3`). |
| **Python-Pakete** | `pip install -r requirements.txt` (installiert `pycdlib` und `py7zr`) |
| **PS2-DVD-Writer** | Enthaltene `mkps2iso`-1.1.1-Werkzeuge für Windows, Linux und macOS |
| **Original-ISO** | Nur US-NTSC-U v1.03 (`SLUS_209.46`). PAL und andere Versionen sind vorübergehend nicht unterstützt. |
| **Freier Speicher** | Mehrere GB – das ISO wird entpackt, das neue ISO daneben geschrieben und Audio-Archive temporär entpackt. |
| **Betriebssystem** | Windows, Linux oder macOS. Keine externen Tools nötig. |

### 🔐 ISO-Prüfsummen

Das Profil US-NTSC-U v1.03 wird anhand dieses Referenz-Images geprüft:

```
MD5:  c383c015065f8060343032480928d08d
SHA1: 66cb01a8281cc132e023a1e52afc75d1fad3fbe1
```

Der Builder erkennt die Version über `SYSTEM.CNF` und die Boot-Executable. PAL v1.00 wird vorübergehend abgewiesen: Es erscheint der PS2-Startbildschirm, aber das Spiel startet auch ohne NTSC-spezifische Overlays und Plugins nicht weiter. `--allow-modded` überspringt nur die Prüfsummenprüfung und aktiviert PAL nicht.

Die [experimentellen PAL-Notizen](experimental/pal/README.md) halten den aktuellen Stand und die offenen Ursachen fest.

---

## 🚀 Schnellstart

### 1. Python-Abhängigkeiten installieren

```bash
python -m pip install -r requirements.txt
```

### 2. Original-ISO bereitstellen

Verwende ein legal erworbenes **GTA San Andreas (USA, NTSC-U v1.03)** für PS2. Der Builder prüft die Version automatisch. Lege das ISO in den Projektordner oder übergib den Pfad mit `--iso`.

Vor Änderungen am Build-Ordner erkennt das Tool die Version. NTSC-U v1.03 wird mit MD5/SHA1 geprüft. PAL und andere Versionen werden abgewiesen, bevor der Build-Ordner geändert wird.

### 3. Einrichtung prüfen und bauen

```bash
python build.py check
python build.py
```

In einem Terminal startet `python build.py` den interaktiven Assistenten. Er fragt nach ISO und Ausgabepfad, zeigt die gewählten Optionen und beginnt nach deiner Bestätigung. Den ISO-Pfad kannst du beim Assistenten per Drag & Drop ins Terminal einfügen.

Für einen Build ohne Rückfragen gib den ISO-Pfad direkt an:

```bash
python build.py --iso "D:/Games/Grand Theft Auto - San Andreas.iso" --output "SLUS_209.46.GTA Legacy Alpha build 0.1.9.iso" --build-dir build-ntsc
```

Unter Windows gibt es dafür auch den PowerShell-Wrapper:

```powershell
.\build.ps1 --iso "D:\Games\Grand Theft Auto - San Andreas.iso" --output "SLUS_209.46.GTA Legacy Alpha build 0.1.9.iso" --build-dir build-ntsc
```

Lass für OPL den Präfix `SLUS_209.46` im ISO-Dateinamen stehen. `build-ntsc/` hält die entpackten Dateien dieses Builds getrennt; ein normaler Build löscht und erstellt den jeweils gewählten Build-Ordner neu.

Eine vorhandene Ausgabedatei wird überschrieben. Ein normaler Build erstellt auch den Arbeitsordner `build/` neu. Verwende `--reuse-build` nur, wenn du die dort entpackten Dateien bewusst wiederverwenden möchtest.

### Nützliche erste Befehle

```bash
python build.py --help       # alle Befehle und Optionen anzeigen
python build.py deps         # Python-Pakete prüfen
python build.py info         # Pfade, Stream-Teile und Paketstatus anzeigen
python build.py stages       # Build-Stages auflisten
python build.py --dry-run    # Stage-Plan zeigen; prüft das ISO nicht
```

Ohne `--output` wird der in `config.ini` eingetragene Ausgabepfad verwendet. Teste das fertige Image in **PCSX2** oder auf einer PS2 mit OPL/FreeMcBoot.

---

## 🖥️ Kommandozeile

### Befehle

| Befehl | Beschreibung |
|---|---|
| `all` (Standard) | Interaktiver Assistent im Terminal oder direkter Build mit `--iso` / `--non-interactive`. |
| `iso` | Wie `all`. |
| `wizard` | Interaktiven Build-Assistenten explizit starten. |
| `check` | Nur Preflight (Pakete, Pfade, freier Speicher, ISO-Region und Prüfsummenregeln). |
| `deps` | Fehlende Python-Pakete anzeigen. Mit `--install-deps` werden sie per pip installiert. |
| `stages` | Alle Stages mit ihren Keys auflisten. |
| `info` | Aufgelöste Pfade, Stream-Teile und Paketstatus anzeigen. |
| `clean` | Build-Ordner und Ausgabe-ISO löschen. |

### Stages

| Key | Was er macht |
|---|---|
| `preflight` | Konfiguration, Pakete, freien Speicher, ISO-Region und Prüfsummenregeln prüfen. |
| `prepare` | Sauberen Build-Ordner anlegen (oder vorhandenen behalten). |
| `extract` | Original-ISO in den Build-Ordner entpacken. |
| `overlay` | `src/` über das entpackte ISO kopieren. |
| `audio` | `STREAMS.7z.*`-Teile zusammenfügen und entpacken. |
| `images` | Assets in `gta3.img` und `gta_int.img` mischen. |
| `package` | Build-Ordner als ISO9660-Level-2-Image bauen. |
| `verify` | Fertiges ISO erneut öffnen und Inhalt prüfen. |

### Optionen

Jede Option überschreibt den passenden Wert aus `config.ini`.

| Option | Beschreibung |
|---|---|
| `--iso PATH` | Eingabe-ISO. |
| `--output PATH` | Ausgabe-ISO. |
| `--config PATH` | Zu lesende Konfigurationsdatei (Standard `config.ini`). |
| `--project-dir PATH` | Quellordner mit den Mod-Dateien (Standard `./src`). |
| `--build-dir PATH` | Arbeitsordner für das entpackte ISO (Standard `./build`). |
| `--only STAGE[,STAGE...]` | Nur diese Stages ausführen. |
| `--skip STAGE[,STAGE...]` | Diese Stages überspringen. |
| `--allow-modded` | Prüfsummen-Prüfung des ISOs überspringen. |
| `--reuse-build` | Vorhandene Extraktion wiederverwenden statt neu zu entpacken. |
| `--clean` | Sauberen Build erzwingen (Build-Ordner löschen). Standard, außer `--reuse-build` ist gesetzt. |
| `--install-deps` | Python-Pakete aus `requirements.txt` vor dem Lauf installieren. |
| `--dry-run` | Plan anzeigen, ohne etwas zu verändern. |
| `--non-interactive` | Niemals den interaktiven Assistenten starten; nur config.ini und CLI-Optionen verwenden. |
| `-v`, `--verbose` | Debug-Logging inkl. jeder hinzugefügten Datei. |
| `-h`, `--help` | Alle Optionen anzeigen. |

Beispiele:

```bash
python build.py                              # interaktiver Assistent
python build.py wizard                       # dasselbe, explizit
python build.py --non-interactive            # direkter Build mit config.ini, ohne Rückfragen
python build.py --iso "path/to/game.iso"     # direkter Build mit bestimmtem ISO
python build.py --only preflight,prepare,extract   # nach dem Entpacken stoppen
python build.py --skip audio                       # ohne Radio-Streams bauen
python build.py --dry-run                          # nur den Plan zeigen
```

`python buildiso.py` funktioniert weiterhin aus Kompatibilitätsgründen und führt alle Stages aus; `python build.py` ist der empfohlene Einstiegspunkt.

Das Tool endet mit `0` bei Erfolg und `1` bei einem Build-Fehler (mit lesbarer Meldung statt Traceback).

---

## ⚙️ config.ini

```ini
[DEFAULT]
iso_name = Grand Theft Auto - San Andreas (USA) (v1.03).iso
output = GTA V Legacy Closed Alpha.iso
project_path = ./src
build_path = ./build
allow_modded = False
reuse_build = False
```

| Schlüssel | Bedeutung |
|---|---|
| `iso_name` | Pfad/Name des Original-ISOs (relativ zum aktuellen Arbeitsordner; normalerweise dem Projektordner). |
| `output` | Name des fertigen ISOs. Wird bei jedem Build überschrieben. |
| `project_path` | Quellordner mit den Mod-Dateien. |
| `build_path` | Arbeitsordner für das entpackte ISO. **Wird bei jedem Build gelöscht**, außer `reuse_build`/`--reuse-build` ist gesetzt. |
| `allow_modded` | `True` = Prüfsummen-Prüfung des ISOs überspringen. |
| `reuse_build` | `True` = vorhandene `build/`-Extraktion weiterverwenden (schneller, aber alte Dateien können ins ISO gelangen). |

Das Skript schreibt `config.ini` nicht mehr zurück; der alte Abschnitt `[SAVED_CONFIG]` ist entfallen. Die früheren Keys `uiso_path` und `imgconsole_path` sind überflüssig, weil keine externen Tools mehr benutzt werden.

---

## 🔧 Wie der Build abläuft

`build.py` führt die Stages aus `buildiso.py` in dieser Reihenfolge aus (`--only`/`--skip` ändern das):

1. **Preflight** – Projektordner, Python-Pakete, freier Speicher und Eingabe-ISO (Existenz + optional MD5/SHA1). Das passiert *bevor* etwas gelöscht wird, damit ein Tippfehler keine bestehende Extraktion vernichtet.
2. **Build-Ordner vorbereiten** – `build/` wird entfernt (außer bei Wiederverwendung) und neu angelegt.
3. **ISO entpacken** – rekursiv nach `build/` via `pycdlib`.
4. **Mod-Dateien kopieren** – `intro/`, `text/`, `data/`, `models/`, `audio/CONFIG`, `audio/SFX`, `anim/`, `plugins/` sowie die Inhalte von `overlays/`. Die GTA-V-Introclips ersetzen `MOVIES/VCNTSC.PSS` und `MOVIES/OPEN1.PSS` aus San Andreas; nur das geteilte Archiv `models/gta3_1.img` wird entfernt.
5. **Audio-Streams entpacken** – alle `STREAMS.7z.*`-Teile in `src/audio/STREAMS/` werden zu `result.7z` zusammengefügt, entpackt und das Archiv gelöscht.
6. **IMG-Archive neu bauen** – jede Datei unter `src/assets/` wird von `imgtool.py` in `gta3.img`/`gta_int.img` gemischt: vorhandene Einträge werden ersetzt, neue angehängt. Die Archive werden Sektor für Sektor neu geschrieben und müssen nie komplett in den Speicher.
7. **ISO schreiben** – die enthaltenen `mkps2iso`-Werkzeuge erzeugen ein PS2-DVD-Image mit UDF-Dateisystem, ISO9660-Brücke, Boot-Kennungen und zur Region passendem Startlogo. Der Builder prüft die Type-L- und Type-M-Pfadtabellen an den Sektoren 257 und 259.
8. **Ergebnis prüfen** – das ISO wird erneut geöffnet und muss `SYSTEM.CNF`, die Executable der erkannten Region, `MODELS/GTA3.IMG` und `MODELS/GTA_INT.IMG` enthalten; Datei- und Ordneranzahl werden ausgegeben.

Erwartete Ausgabe (grob):

```
GTA V Legacy builder v0.4
      Project: src
      Build:   build
      Output:  GTA V Legacy Closed Alpha.iso

[1/8] Checking configuration and input ISO ...
      ISO: Grand Theft Auto - San Andreas (USA) (v1.03).iso
      Free space (build folder): 120.4 GiB
      done in 3.1 s
[2/8] Preparing build folder ...
      done in 8 ms
[3/8] Extracting ISO ...
      done in 42.6 s
[4/8] Copying mod files ...
      done in 2.4 s
[5/8] Unpacking audio streams ...
      done in 55.1 s
[6/8] Rebuilding IMG archives ...
      gta3.img: 10632 entries (412 replaced, 96 added, 1.1 GiB)
      gta_int.img: 1221 entries (18 replaced, 0 added, 98.0 MiB)
      done in 1 min 12 s
[7/8] Writing ISO ...
      Packaging 78 files ...
      done in 2 min 3 s
[8/8] Verifying output ...
      GTA V Legacy Closed Alpha.iso (4.2 GiB)
      78 files, 24 folders
      done in 1.2 s

Done. 8 stage(s) in 5 min 14 s.
```

Hinweise zu den Formaten der Python-Implementierung:

- IMG-Archive sind **VER2** (GTA San Andreas). Einträge sind auf 65535 Sektoren (~128 MiB) und 23 Zeichen Namen begrenzt, genau wie bei den Original-Tools. Verstöße brechen den Build mit klarer Meldung ab.
- Das finale Image wird mit `mkps2iso` 1.1.1 erstellt. Dabei entstehen die PS2-DVD-UDF-Strukturen und die ISO9660-Brücke. Der Build prüft die UDF-Volume-Sequenz und den Anker, die Systemkennung `PLAYSTATION` sowie die Pfadtabellen an den Sektoren 257 und 259. Werkzeug und Lizenz liegen in `tools/mkps2iso/`. PNG-/PSD-Arbeitsgrafiken und IDE-Metadaten kommen nicht ins Spiel-Image.
- Das ISO wird aus den Dateiinhalten neu gebaut, nicht Byte für Byte am Original gepatcht. Die Verzeichnisreihenfolge kann daher von der Retail-Disc abweichen.

---

## 🗂️ Projektstruktur

```
GTAVLegacy/
├─ build.py                  # Zentrales Build-Tool (Einstiegspunkt, CLI)
├─ buildiso.py               # Build-Stages: preflight … verify (auch direkt nutzbar)
├─ imgtool.py                # IMG-(VER2-)Reader/Writer, reines Python
├─ build.ps1                 # PowerShell-Wrapper, reicht Argumente an build.py weiter
├─ config.ini                # Pfade & Optionen
├─ requirements.txt          # pycdlib, py7zr
├─ tools/mkps2iso/           # enthaltene PS2-DVD-Tools und Lizenz
├─ tests/test_smoke.py       # End-to-End-Test mit Fake-ISO
├─ .githooks/                # optionaler prepare-commit-msg-Co-Author-Hook
├─ IMGconsole_32-bit/        # Legacy: fastman92 IMG Console, ungenutzt
├─ music-installer/          # Legacy: GTA-SA-Musik-/Audio-Installer-Tools
├─ legalize/                 # normalisiertes GTA-V-Audio (Cutscenes, Stimmen, Musik)
├─ src/                      # Alle Mod-Inhalte
│  ├─ anim/                  # IFP-Animationen (ped.ifp, gangs.ifp)
│  ├─ assets/                # Quelldateien, die in die IMGs wandern
│  │  ├─ Anims/  Map/  Peds/  Radar/  Vegetation/
│  │  ├─ Vehicles/  Weapons/  Interiors/
│  │  ├─ Cars to convert/    # noch nicht konvertierte GTA-V-Modelle
│  │  ├─ Maps to convert/  Objects to convert/  Wrecked cars/
│  │  └─ build.txt           # Legacy-IMG-Console-Skript, ungenutzt
│  ├─ audio/                 # CONFIG/, SFX/ und STREAMS/ (7z-Teile)
│  ├─ data/                  # GTA-SA-Datentabellen (handling, ide, ipl ...)
│  ├─ intro/                 # GTA-V-Startlogo und Ladeclips (RGM)
│  ├─ models/                # IMGs, TXDs, Effekte, HUD
│  ├─ overlays/              # PS2-Overlays: INIT.NM, FILELOAD.NM, relocator.nm
│  ├─ plugins/               # CLEO/Opcode-Patches (.dep) + plugins.ini
│  ├─ text/                  # AMERICAN.GXT/INI
│  └─ STREAM.INI
├─ plugins/                  # Arbeitsordner/Platzhalter für Plugin-Unterordner
├─ SLUS_209.46               # PS2-Executable von GTA San Andreas (NTSC-U)
├─ Wav 2 GTA V Legacy PS2.exe # Tool zum Konvertieren von WAVs in PS2-Streams
└─ *.png / *.dds             # HUD-, Radar- und Shop-UI-Grafiken
```

Wichtig: `build/` und die temporären `IMGconsole_32-bit/gta3*`-Ordner sind **Artefakte**, keine Quelle (und per `.gitignore` ausgeschlossen). Änderungen gehören immer nach `src/`.

---

## 📝 Sprache und Benennung

Das Repository ist englisch-first, damit international daran gearbeitet werden kann:

| Regel | Grund |
|---|---|
| Ordner, Dateinamen, Code, Kommentare und Doku sind Englisch. | Hält Build und Workflow für alle verständlich. |
| [`README.de.md`](README.de.md) ist die einzige deutsche Datei. | Sie ist eine ausdrückliche Übersetzung, nicht die Hauptdokumentation. |
| Spieldaten behalten ihre Originalnamen (`HANDLING.CFG`, `VEHICLES.IDE`, `GTA3.IMG`, …). | Die Engine sucht sie über den Namen; Umbenennen bricht das Spiel. |
| Konvertierte Modelle und Texturen behalten ihre Asset-Namen (`stretch.dff`, `comet.txd`, …). | IDE-Dateien und Skripte referenzieren sie über den Namen. |
| PS2-DVD-Layout / Dateinamen | Erstellt mit enthaltenem `mkps2iso`; ISO9660-Level-2-Namen sind auf 31 Zeichen begrenzt. |

Nicht-englische Legacy-Ordner wurden übersetzt: `Instalador de Musicas` → `music-installer`, `legalize/legalize/falas` → `voices`, `legalize/legalize/musicas` → `music`; die russischen Ordner unter `src/assets/Cars to convert/` sind jetzt ebenfalls Englisch. Auch die fremdsprachigen Readmes in den konvertierten Asset-Paketen wurden übersetzt.

---

## 🎨 Assets hinzufügen

### Fahrzeuge, Waffen, Peds, Map-Objekte

1. Neuen Ordner unter der passenden Kategorie anlegen, z. B.:
   ```
   src/assets/Vehicles/Cars/MeinAuto/mein_auto.dff
   src/assets/Vehicles/Cars/MeinAuto/mein_auto.txd
   ```
2. Der Build mischt den kompletten Ordner rekursiv in `gta3.img`. Dateien mit den Endungen `.txt`, `.cfg`, `.ide`, `.dat` sowie typische Betriebssystem-Metadaten wie `desktop.ini` werden **ignoriert** – praktisch für Notizen und Windows-Ordner.
3. Einträge in `src/data/VEHICLES.IDE`, `HANDLING.CFG`, `CARCOLS.DAT`, `CARMODS.DAT` usw. ergänzen, sonst ist das Modell im Spiel nicht nutzbar.
4. Textur-/Modellnamen müssen zur IDE-Datei passen.

### Peds und Map

Gleiches Prinzip: Ordner unter `src/assets/Peds/` bzw. `src/assets/Map/`, dazu passende Einträge in `PEDS.IDE`, `DEFAULT.IDE`, den IPL-Dateien unter `src/data/MAPS/`.

### Interiors

Alles unter `src/assets/Interiors/` landet in `gta_int.img`.

### HUD / Texturen

TXDs (z. B. `VLHUD.TXD`) nach `src/models/` bzw. `src/models/txd/` legen. Die PNG/DDS-Dateien im Root sind Zwischenstände bzw. Quellen für die TXDs.

---

## 🎧 Audio / Radio-Streams

Die GTA-V-Sender liegen als mehrteiliges 7z-Archiv vor:

```
src/audio/STREAMS/STREAMS.7z.001 … STREAMS.7z.085
```

Der Build erkennt die Teile automatisch und fügt sie in numerischer Reihenfolge zusammen:

```python
parts = collect_stream_parts(project / "audio" / "STREAMS")
```

Du kannst Teile frei hinzufügen oder entfernen – es gibt keine `range()`-Konstante mehr zu pflegen. Hat die Nummerierung Lücken, gibt der Build eine Warnung aus statt still kaputtes Audio zu erzeugen.

Zum Erzeugen eigener Streams liegt `Wav 2 GTA V Legacy PS2.exe` im Repo-Root (Windows). Konvertiere damit WAV-Dateien und lege das Ergebnis in `src/audio/STREAMS/` ab.

`sfx-tool/`, `music-installer/` und `IMGconsole_32-bit/` sind Legacy-Authoring-Helfer aus dem Originalprojekt (nur Windows). Sie werden zum ISO-Build **nicht** benötigt: `build.py` ersetzt die IMG Console und nutzt die vorbereiteten Audiodateien aus `src/` direkt.

Fehlt der Ordner komplett, warnt der Build und läuft ohne eigenes Audio weiter.

---

## ⚠️ Bekannte Stolperfallen

| Problem | Ursache / Lösung |
|---|---|
| Prüfsummen- oder Versionsfehler | Verwende US-NTSC-U v1.03. `--allow-modded` überspringt nur die Prüfsummenprüfung; PAL und andere Versionen bleiben gesperrt. |
| Weißer Bildschirm in OPL | Prüfe die Boot-ID in `SYSTEM.CNF`; `PAL Safe Boot Test.iso` ist PAL (`SLES_529.27`), nicht NTSC. Lass GSM und Kompatibilitätsmodi auf Standard. Bei USB/Netzwerk den alten Namen `SLUS_209.46.Spielname.iso` probieren; OPL nennt das als Workaround für manche Spiele. |
| `gta3.img` nicht gefunden | Die ISO-Extraktion ist unvollständig – `build/` löschen und neu bauen. |
| Alte Assets im ISO | `reuse_build = True` oder `--reuse-build` war aktiv. Mit `--clean` bauen. |
| `... cannot be stored in a plain ISO9660 image` | Ein Name in `build/` ist länger als 31 Zeichen oder enthält ungültige Zeichen. In `src/` umbenennen. |
| `Entry name ... is N characters long` | IMG-Eintragsnamen sind auf 23 Zeichen begrenzt. |
| `needs N sectors, the format only allows 65535` | Eine Datei ist größer als ~128 MiB und passt nicht in ein VER2-Archiv. |
| Hoher Speicherbedarf | Die 7z-Teile werden als ein `result.7z` in `build/` zwischengespeichert; genug freien Platz einplanen. |
| Audio fehlt im Spiel | `STREAMS.7z.*`-Teile unvollständig oder mit Lücken in der Nummerierung (siehe Warnung). |
| Absturz beim Laden | Meist fehlende IDE-/IPL-/Handling-Einträge für neu hinzugefügte Assets. |
| Python-Paket fehlt | `pip install -r requirements.txt`. |

In dieser Weiterführung behoben (gegenüber dem Original-Skript):

- Läuft unter Windows, Linux und macOS: ISO-Pakete werden mit enthaltenem `mkps2iso` erstellt, IMG-Archive verarbeitet `imgtool.py`.
- `build.ps1` ruft nicht mehr das unter Windows fehlende `python3` auf.
- `result.7z` wird frisch (`wb`) statt im Append-Modus (`ab`) geschrieben – Rebuilds können es nicht mehr korrumpieren.
- Fehler werden als lesbare Meldung mit Exit-Code `1` ausgegeben statt als Traceback.
- Das ISO wird *vor* dem Löschen des Build-Ordners validiert.
- Die Anzahl der Audio-Teile wird erkannt statt hartkodiert.
- Jede Option lässt sich über die Kommandozeile überschreiben.
- Es gibt einen End-to-End-Smoke-Test, der ein komplettes (winziges) ISO baut.

Verbleibende technische Schulden:

- Keine Asset-Validierung (fehlende TXD-/IDE-Referenzen werden nicht erkannt).
- Das erzeugte ISO nutzt ein frisches Layout statt der Retail-Disc-Reihenfolge.
- Nur `gta3.img` und `gta_int.img` werden neu gebaut; `player.img` bleibt unangetastet.

---

## 🧭 Projekt weiterführen

Roadmap für die nächsten Schritte:

1. **Bestandsaufnahme** – Welche Assets sind fertig konvertiert, welche liegen nur unter `* to convert/`? TODOs aus `src/assets/*/build.txt` und den `.txt`-Notizen sammeln.
2. **Asset-Pipeline dokumentieren** – Welche Tools (Blender, ZModeler, Magic.TXD, …) und welche Konvertierungsschritte führen von GTA V zu PS2-kompatiblen DFF/TXD? Das ist der größte Wissensverlust im Repo.
3. **Validierung** – Vor dem ISO-Bau prüfen, ob jedes DFF eine passende TXD und einen IDE-Eintrag hat; fehlende Referenzen als Warnung ausgeben.
4. **Kompatibilitätstest auf Hardware** – Ein Release-Build in PCSX2 und auf einer echten PS2 (OPL/FreeMcBoot) prüfen, inklusive Audio-Streaming.
5. **Release-Prozess** – Versionierung, Changelog, Hash des erzeugten ISOs veröffentlichen.
6. **Aufräumen** – Die Legacy-Tools in `IMGconsole_32-bit/` und `src/assets/build.txt` entfernen, sobald sich der Python-Build bewährt hat.

Beim Weiterentwickeln gilt: **`src/` ist die Quelle der Wahrheit.** Alles, was nur in `build/` oder `IMGconsole_32-bit/` liegt, ist wegwerfbar.

---

## 📤 Fork veröffentlichen

`origin` zeigt auf die Weiterführung, `upstream` auf das Originalprojekt:

```bash
git remote -v
# origin   https://github.com/baummarder/GTAVLegacyRW.git
# upstream https://github.com/DanielSant0s/GTAVLegacy.git

git push -u origin main
```

Setze in den GitHub-Repository-Einstellungen eine Beschreibung wie:

> Continuation of GTA V Legacy (PS2) by Daniel Santos – GTA V content for GTA San Andreas on PlayStation 2.

Veröffentliche **keine** ISO-Dateien oder Spiel-Assets, die du nicht weitergeben darfst.

---

## 🧪 Hinweise für Entwickler

### Tests

```bash
python -m unittest discover -s tests -v
```

Der Smoke-Test erzeugt ein Miniatur-ISO mit derselben Struktur, führt den kompletten Build aus und prüft die entstandenen Archive und das Image. Er braucht keine Spieldaten.

### KI-Co-Autoren

Die Identitäten von Devin und OpenCode stehen für Commits bereit, zu denen sie beigetragen haben. Der `prepare-commit-msg`-Hook fügt sie standardmäßig nicht hinzu. Für einen einzelnen Commit kannst du ihn über `GTAV_ADD_AI_COAUTHORS=1` in dessen Umgebung aktivieren:

```
Co-authored-by: Devin <158243242+devin-ai-integration[bot]@users.noreply.github.com>
Co-authored-by: opencode-agent[bot] <opencode-agent[bot]@users.noreply.github.com>
```

Den Hook einmal pro Clone aktivieren:

```bash
git config core.hooksPath .githooks
```

Die Identitäten bleiben aus Commits heraus, sofern du nicht `GTAV_ADD_AI_COAUTHORS=1` für einen Commit setzt oder die Trailer selbst einfügst. Der Hook überspringt Merge-/Squash-/Fixup-Commits und überschreibt keine vorhandenen Co-Author-Trailer.

### Am Build-Skript arbeiten

```bash
python build.py                 # interaktiver Assistent
python build.py wizard --dry-run  # Stage-Plan zeigen
python build.py --help            # ohne ISO oder Abhängigkeiten
python build.py --dry-run         # Stage-Plan zeigen
python build.py -v                # kompletter Build mit Debug-Ausgabe
python build.py --skip audio      # ohne Radio-Streams bauen
python build.py --reuse-build     # vorhandenes build/ nicht neu entpacken
python build.py stages            # Stage-Keys auflisten
```

---

## ⚖️ Rechtliches

- Der Code dieses Repos steht unter der **MIT License** (siehe `LICENSE`, © 2023 Daniel Santos, © 2026 Baummarder).
- **GTA San Andreas** und **GTA V** sowie alle Assets sind Eigentum von **Rockstar Games / Take-Two Interactive**.
- Das Repo enthält **kein** vollständiges Spiel und darf nicht als solches weitergegeben werden. Du brauchst eine legal erworbene Kopie von GTA San Andreas (PS2).
- Dieses Projekt ist ein inoffizielles Fanprojekt und steht in keiner Verbindung zu Rockstar Games.

---

## 🙌 Credits

- **Daniel Santos** ([@DanielSant0s](https://github.com/DanielSant0s)) – ursprüngliches GTAVLegacy-Projekt, Build-Skript, Asset-Konvertierung, PS2-Overlays
- **@baummarder** – Maintainer dieser Weiterführung
- **fastman92** – IMG Console (im Original-Build genutzt, jetzt durch `imgtool.py` ersetzt)
- **mkps2iso** – PS2-DVD-Erstellung (unter GPL-2.0 enthalten; siehe `tools/mkps2iso/LICENSE`)
- **pycdlib**, **py7zr** – Python-Bibliotheken für ISO- und 7z-Verarbeitung
- **Devin**, **opencode-agent[bot]** und **DeepSeek** – KI-Unterstützung bei Dokumentation, Build-Tooling und Wartung dieser Weiterführung
