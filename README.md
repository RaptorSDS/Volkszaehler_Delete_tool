# Volkszaehler_Delete_tool
small tool to delete value in Volkszaehler DB 

projekt startet as Powershell 
V0.4b as reference work quiet good
v0.5b with some tweak (untestet)

follow by phython with tkinter interface also as Windows 7/8/10/11 (without UAC) 

v0.5b testet and work 

v0.8b experimental with negativ numbers support (untested , i have no db with negativ numbers)

Data Deletion Tool v0.5b
By Tobias aka Raptorsds (github.com/raptorsds)
Created with Claude | MIT License

This tool helps you delete data points that exceed a specified maximum value.

Instructions:
1. Server Address: Enter the IP or domain name without http:// or https://
2. UUID: Enter the UUID of the data set you want to process
3. Start/End Time: Enter time range in dd.MM.yyyy HH:mm format or as UNIX timestamp
4. Max Value: Enter the threshold value (any data point above this will be deleted)
   - Use the +/- selector to set positive or negative thresholds
   - For negative thresholds, values below the threshold will be deleted
   - Example: With -4000, values like -6000 will be deleted, but -3990 will remain
5. Processing Delay: Select appropriate delay based on your system:
   - 200ms: Fast local x86 systems
   - 500ms: Server environments (local or remote)
   - 1000ms: Raspberry Pi or similar devices
   - 2000ms: Slow systems or high-latency connections

The tool will fetch data points and delete any that exceed the specified max value.
Progress and results will be shown in the log area.


Anweisungen:
1. Server-Adresse: Geben Sie die IP-Adresse oder den Domänennamen ohne http:// oder https:// ein.
2. UUID: Geben Sie die UUID des Datensatzes ein, den Sie verarbeiten möchten.
3. Start/Endzeit: Geben Sie den Zeitbereich im Format tt.MM.jjjj HH:mm oder als UNIX-Zeitstempel ein.
4. Höchstwert: Geben Sie den Schwellenwert ein (alle Datenpunkte, die über diesem Wert liegen, werden gelöscht)
   - Verwenden Sie den +/- Wähler, um positive oder negative Schwellenwerte festzulegen
   - Bei negativen Schwellenwerten werden Werte unterhalb des Schwellenwertes gelöscht.
   - Beispiel: Bei -4000 werden Werte wie -6000 gelöscht, aber -3990 bleiben erhalten.
5. Verarbeitungsverzögerung: Wählen Sie die für Ihr System geeignete Verzögerung:
   - 200ms: Schnelle lokale x86-Systeme
   - 500ms: Server-Umgebungen (lokal oder remote)
   - 1000ms: Raspberry Pi oder ähnliche Geräte
   - 2000ms: Langsame Systeme oder Verbindungen mit hoher Latenz

Das Tool holt Datenpunkte ab und löscht alle, die den angegebenen Maximalwert überschreiten.
Der Fortschritt und die Ergebnisse werden im Log-Bereich angezeigt.

