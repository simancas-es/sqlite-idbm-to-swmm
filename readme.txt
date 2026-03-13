About: creating an .exe:
python -m pip install pyinstaller
python -m pip install -r requirements.txt
Then:
pyinstaller src/main.py -p src/
pyinstaller -F src/main.py -p src/
Or:
python -m PyInstaller src/main.py -p src/
python -m PyInstaller -F src/main.py -p src/


About: sqlite Spatialite extension:
Sqlite must have been compiled with the possibility of enabling extensions.
NOTE: if for some reason this .dll doesn't work, try downloading it from the original website. (See --license)


About: /utils:
The created .inp file is the barebones network.
It is recommended to save particular sections of the INP file
so that they can be easily appended at the end later,
in case the network is modified in the future. This may include:
Dry weather flows, network profiles for show, patterns, curves, config, etc.
Edit the quickappend.cmd as needed.

About: /examples/RegenschreiberZuordnung.csv:
Headers are important. SCID : Subcatchment ID as available in the IDBM Database.
Assignation is possible in a program like QGIS, as the IDBM Database
already contains the geometry of the points. So by dragging and dropping
the file into QGIS it can be loaded instantly, and by using polygon areas
with Regenschreiber IDs, a relation of SCID - RSIDs can be obtained.

About: running from terminal:
main.exe --sqliteidbm example.idbm --output example.inp --regenschreiber examples/RegenschreiberZuordnung.csv --log conversionerror.log --dump-csv folder --spatialite-dll mod_spatialite.dll --force