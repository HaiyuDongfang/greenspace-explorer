# Auckland Greenspace Explorer: Agent Conventions

## Scope and safety

- Only read, create, and modify files inside this project directory.
- Never move, overwrite, rename, or delete the user's original GIS datasets.
- Keep raw GIS data outside Git and never copy large datasets into the repository.
- Prefer project-relative paths through `pathlib.Path`; use environment-configured external paths for production datasets.
- Do not add machine-specific absolute paths, credentials, tokens, or private local configuration.
- Ask before installing packages or changing dependency declarations.

## Architecture

- Keep Shiny UI components under `src/ui/`.
- Keep GIS loading, validation, spatial joins, filtering, and measurements in data-processing modules under `src/data/` and the public service module `src/data_processing.py`.
- Keep reactive application state separate from rendering and spatial calculations.
- Do not place business rules inside UI component functions.
- Use small, typed functions that can be tested independently of Shiny and ipyleaflet.

## GIS conventions

- Do not invent park-duration fields or assumptions. Confirm field names and analytical semantics from the supplied data or project documentation before use.
- Validate CRS, geometry types, null geometries, and invalid geometries before calculations.
- Do not silently change CRS. Document every reprojection and target projected CRS.
- State and test the unit and definition of area, route length, and walking duration.
- Do not silently discard unclassified network types; preserve them for review.
- Treat overlapping, duplicated, clipped, and park-boundary-crossing network features explicitly.

## Data conventions

- Only commit small, reviewed, purpose-built demo files under `data/demo/`.
- Do not commit `data/raw/`, `data/external/`, GeoPackage/Shapefile components, or large GeoJSON files.
- Never infer placeholder demo attributes in production summaries.
- Keep large and generated outputs out of source control.

## UI conventions

- Preserve a full-screen map-centred layout.
- Keep the filters, results, details, and status bar separate UI modules.
- Preserve filter and list state when navigating between results and park details.
- Use reactive state instead of browser-only state when server-side computation depends on it.
- Keep custom styling in `www/styles.css`.

## Validation

- Run syntax checks and focused tests after substantive code changes.
- Do not claim runtime or map validation when dependencies have not been installed or the application has not been launched.
- Add a regression test for spatial or stateful behavior whenever fixing a bug.
- Report warnings and uncertainties rather than masking missing data with guessed values.

## Git conventions

- Do not rewrite history, force-push, or commit unless explicitly requested.
- Preserve unrelated user changes in dirty working trees.
