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

1. Server-Adresse: IP-Adresse oder Hostname der Middleware
   - optional mit `http://` oder `https://` (Standard: `http://`)
   - optional mit Port, z.B. `vz.example.com:8080`
   - optional mit Middleware-Pfad, z.B. `https://vz.example.com/middleware.php`
   - Beispiele: `192.168.1.100` · `raspberrypi` · `vz.example.com:8080` · `https://vz.example.com/middleware.php`
2. UUID: UUID des Kanals, der bereinigt werden soll
3. Start/Endzeit: Zeitbereich im Format `tt.MM.jjjj HH:mm` (Ortszeit des PCs) oder als
   UNIX-Zeitstempel in ms. Die Startzeit muss vor der Endzeit liegen.
4. Höchstwert: Schwellenwert
   - `+`: alle Datenpunkte über dem Schwellenwert werden gelöscht (geprüft wird `max`)
   - `-`: alle Datenpunkte unter dem negativen Schwellenwert werden gelöscht (geprüft wird `min`)
   - Beispiel: Bei -4000 werden Werte wie -6000 gelöscht, -3990 bleibt erhalten
5. Verarbeitungsverzögerung:
   - 200 ms: Schnelle lokale x86-Systeme
   - 500 ms: Server-Umgebungen (lokal oder remote)
   - 1000 ms: Raspberry Pi oder ähnliche Geräte
   - 2000 ms: Langsame Systeme oder Verbindungen mit hoher Latenz
6. Testlauf (Dry run): zeigt nur an, welche Datenpunkte über dem Schwellenwert liegen, löscht
   nichts. Bei Zähler-Kanälen ist das eine Schätzung, weil sich durch das Löschen eines
   Messwerts der berechnete Wert des folgenden Intervalls ändert.

Fortschritt und Ergebnisse werden im Log-Bereich angezeigt. Das Log wird zusätzlich pro Tag
als Datei gespeichert (Button „Open Log Folder“), die letzten Eingaben werden beim nächsten
Start wiederhergestellt. Beides liegt unter `%APPDATA%\VZ_Delete_Tool\`.

Sicherheitsfunktionen:
- Meldet die Middleware einen Fehler (z.B. fehlendes DELETE-Recht), bricht das Tool mit der
  Fehlermeldung der Middleware ab.
- Taucht ein bereits gelöschter Zeitstempel erneut auf, bricht das Tool ab statt endlos zu löschen.
- Alle HTTP-Anfragen haben ein Timeout, das Tool hängt nicht bei nicht erreichbarem Server.

## Projektstruktur

```
src/vz_delete_tool.py         aktuelle Version (Python / tkinter)
requirements.txt              Python-Abhängigkeiten
tests/                        Unit-Tests (python -m unittest discover -s tests)
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

## Versionshistorie

| Version | Typ | Status |
|---------|-----|--------|
| v0.4 | PowerShell | Referenz, funktioniert gut |
| v0.5b | PowerShell | einige Anpassungen (ungetestet) |
| v0.5b | Python/tkinter | getestet, funktioniert |
| v0.8b | Python/tkinter | experimentell: negative Schwellenwerte, Verzögerung wählbar |
| v0.9 | Python/tkinter | Basis v0.8b: Hilfe zur DB-Freigabe, Fehlerkorrekturen (Zeitzone, negative Werte über `min`, Endlosschleifen-Schutz, Thread-Sicherheit, Timeouts), Server mit https/Port/Pfad, Testlauf, Log-Datei, gespeicherte Eingaben, EXE-Build per GitHub Actions |

## Lizenz

MIT – Tobias aka Raptorsds · erstellt mit Claude
