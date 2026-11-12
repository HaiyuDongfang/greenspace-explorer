# Auckland Greenspace Explorer

A research-oriented Python Shiny application for exploring walking networks in Auckland's public greenspaces.

## Stack

- Shiny for Python for the application shell and reactive UI
- GeoPandas, PyProj and Shapely for GIS processing
- ipyleaflet for interactive maps
- shinywidgets for Shiny widget integration
- Plotly for optional summaries and charts

This repository currently contains the initial project skeleton and small demonstration data. It does not yet implement the full Park Finder or production GIS workflows.

## Windows setup

Run the following in PowerShell from the project directory.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks virtual environment activation, run this once for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## Run locally

```powershell
shiny run --reload app.py
```

Open the local URL printed by Shiny. The demo uses `data/demo/parks.geojson` and `data/demo/networks.geojson`.

## ShinyLive deployment

The existing GitHub Pages export is in `docs/`. In Pyodide the walking-network
GeoPackage is read with Fiona; local Python continues to use pyogrio. The
export must include the Pyodide-compatible Fiona and PyArrow packages and the
runtime datasets at their existing project-relative paths.

When rebuilding the export, use a staging directory containing only the
application and required runtime files: ShinyLive embeds files from its input
directory, including files ignored by Git. Review `docs/app.json` before
publishing to avoid exposing unintended local data.

## Production data

Raw and large datasets should remain outside Git. Configure external files with environment variables:

```powershell
$env:GREENSPACE_PARKS_PATH = "D:\path\to\parks.geojson"
$env:GREENSPACE_NETWORKS_PATH = "D:\path\to\networks.geojson"
$env:GREENSPACE_AREAS_PATH = "D:\path\to\areas.geojson"
```

The Python configuration in `config/paths.py` also provides project-relative fallbacks. Paths are resolved with `pathlib`; do not add machine-specific absolute paths to source files.

## Project layout

```text
app.py                 Shiny entry point
src/                   Application modules
src/ui/                UI components
src/data_processing.py GIS loading and validation
config/                Data-path configuration
www/styles.css         Custom application styling
data/demo/             Small reviewed demonstration datasets
data/external/         Ignored external production data location
```
