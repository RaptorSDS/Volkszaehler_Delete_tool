# Volkszaehler_Delete_tool

Kleines Tool zum Löschen von Ausreißer-Werten (Spikes) in einer
[Volkszähler](https://volkszaehler.org)-Datenbank über die Middleware-HTTP-API.
Small tool to delete outlier values in a Volkszaehler DB via the middleware HTTP API.

Das Tool holt für einen Kanal (UUID) und einen Zeitraum den Maximalwert, löscht
ihn, wenn er über dem Schwellenwert liegt, und wiederholt das, bis kein Wert mehr
über dem Schwellenwert liegt.

## Download

Fertige Windows-EXE-Dateien gibt es unter
[Releases](https://github.com/RaptorSDS/Volkszaehler_Delete_tool/releases):

| Datei | System |
|-------|--------|
| `VZ_Delete_Tool_vX.Y.exe` | Windows 10 / 11 |
| `VZ_Delete_Tool_vX.Y_win7.exe` | Windows 7 / 8 (mit Python 3.8 gebaut) |

Keine Installation und keine Admin-Rechte (UAC) nötig.

## Voraussetzung: DELETE-Recht für den Datenbank-Benutzer

Damit die Middleware Datensätze per HTTP löschen darf, braucht der MySQL-Benutzer
`vz@localhost` das `DELETE`-Recht.

**Volkszähler Raspberry-Pi-Image**

```
sudo mysql --user=root -praspberry
mysql> grant select, update, insert, delete on volkszaehler.* to vz@localhost;
mysql> flush privileges;
mysql> exit
```

**Andere Systeme**

```
grant delete on volkszaehler.* to 'vz'@'localhost';
```

Recht wieder entziehen:

```
revoke delete on volkszaehler.* from 'vz'@'localhost';
```

## Bedienung

1. Server-Adresse: IP-Adresse oder Domainname ohne `http://` oder `https://`
2. UUID: UUID des Kanals, der bereinigt werden soll
3. Start/Endzeit: Zeitbereich im Format `tt.MM.jjjj HH:mm` oder als UNIX-Zeitstempel (ms)
4. Höchstwert: Schwellenwert – alle Datenpunkte darüber werden gelöscht
   - Mit dem +/- Wähler positive oder negative Schwellenwerte festlegen
   - Bei negativen Schwellenwerten werden Werte unterhalb des Schwellenwerts gelöscht
5. Verarbeitungsverzögerung:
   - 200 ms: Schnelle lokale x86-Systeme
   - 500 ms: Server-Umgebungen (lokal oder remote)
   - 1000 ms: Raspberry Pi oder ähnliche Geräte
   - 2000 ms: Langsame Systeme oder Verbindungen mit hoher Latenz

Fortschritt und Ergebnisse werden im Log-Bereich angezeigt.

## Projektstruktur

```
src/vz_delete_tool.py         aktuelle Version (Python / tkinter)
requirements.txt              Python-Abhängigkeiten
.github/workflows/build.yml   Build der EXE-Dateien + Release
archive/powershell/           alte PowerShell-Versionen (v0.4, v0.5b)
archive/python/               alte Python-Versionen inkl. EXE (v0.5b, v0.8b)
```

## Selbst starten / bauen

```
pip install -r requirements.txt
python src/vz_delete_tool.py

pip install pyinstaller
pyinstaller --onefile --windowed src/vz_delete_tool.py
```

## Release erstellen

1. `__version__` in `src/vz_delete_tool.py` anpassen und committen
2. Tag passend zur Version setzen und pushen, z.B.:
   ```
   git tag v0.6
   git push origin v0.6
   ```
3. GitHub Actions baut beide EXE-Dateien und hängt sie an ein neues Release.

Bei jedem normalen Push werden die EXE-Dateien ebenfalls gebaut und stehen im
jeweiligen Actions-Lauf als Artefakt zum Download bereit.

## Versionshistorie

| Version | Typ | Status |
|---------|-----|--------|
| v0.4 | PowerShell | Referenz, funktioniert gut |
| v0.5b | PowerShell | einige Anpassungen (ungetestet) |
| v0.5b | Python/tkinter | getestet, funktioniert |
| v0.8b | Python/tkinter | experimentell: negative Schwellenwerte, Verzögerung wählbar |
| v0.6 | Python/tkinter | Basis v0.8b, Hilfe zur DB-Freigabe (DELETE-Recht) mit Kopier-Buttons, EXE-Build per GitHub Actions |

## Lizenz

MIT – Tobias aka Raptorsds · erstellt mit Claude
