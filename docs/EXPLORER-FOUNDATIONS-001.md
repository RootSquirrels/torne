# EXPLORER-FOUNDATIONS-001 — The frontend and the API it serves

> **Nature: application foundations.** This record publishes **no knowledge product** and draws **no
> conclusion** about the ocean, the atmosphere or the markets. It replaces the exploratory interface
> and the exploratory API by a reusable component system and a versioned, typed API, and it checks
> that the Explorer still says the same things. Every statement below was measured by execution on
> 2026-11-01.
>
> **Role in the programme.** Every application the programme will open — Water Intelligence,
> Opportunity Intelligence, the Market branch when it opens — reads the same catalogue through the
> same API and reuses the same components. This mission builds what those applications stand on;
> it does not build them.
>
> **The decisions are in `docs/ADR-EXPLORER-FOUNDATIONS-001.md`.** This record says what was built,
> what was measured, and what remains open.

**Reproduction.**

```bash
# the engine and the API
uv run pytest
uv run ruff check .
uv run ruff format --check .

# the frontend
cd frontend
npm install
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

---

## 1. What the mission established

1. **The frontend is a component system, not a page.** The legacy `app.js` — 529 lines that built
   HTML strings and drove the navigation from functions — is gone. It is replaced by 27 components
   and 82 source files (8 253 lines of TypeScript, TSX and CSS) that receive typed data through
   their props and know nothing about HTTP.
2. **The API is versioned, typed and self-describing.** `/api/v1` is canonical and is the only
   prefix the OpenAPI document describes; `/api` still answers, marked `Deprecation: true` with a
   `Link` header pointing at its successor. Its removal has a published rule — one announced step,
   never a side effect of another change. Every route declares the Pydantic model it serves, and
   every failure carries `detail` and a stable `error.code`.
3. **The Explorer's meaning did not change.** The catalogue, the map, the missions, the assets,
   the sources, the models, the coverages and the results say the same things as before; the
   browser journeys that read them pass against the application FastAPI actually serves.
4. **Nothing depends on a third party at runtime.** The frontiers are built at build time and
   served from the application's own origin: 365 kB, against the 739 kB the CDN used to serve.
5. **The boundaries still hold.** No scientific module imports FastAPI or the explorer; a test
   refuses the repository if one does. The frontend never calls a data provider.

---

## 2. The frontend foundations

### 2.1 A root of its own

`frontend/` is a real project root: `package.json`, `package-lock.json`, `tsconfig.json`,
`vite.config.ts`, `playwright.config.ts`, `eslint.config.js`, `src/`, `tests/`, `scripts/`. The
engine's Python package knows nothing about npm, and the frontend knows nothing about the engine's
classes.

TypeScript is **strict**, with `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` on top:
an absent value has to be handled, not asserted away. `baseUrl` is deliberately absent — it is
deprecated in TypeScript 6.

The build writes into the Python package (`src/torne/explorer/static/`), so the wheel is
self-contained and the thing the browser tests exercise is the thing that ships.

The compiled tree holds a `data/` directory, and the repository's `data/` ignore rule matches any
directory of that name at any depth. The two directories that must be tracked — the vendored
frontiers in `frontend/public/data/` and their compiled copy — are therefore re-included
explicitly; without that, the frontiers would have been silently absent from the history.

### 2.2 The design system

`src/styles/tokens.css` is the single source of the surface, the typography, the spacing, the
states and the palettes. Light and dark are expressed with `light-dark()` against a single
`color-scheme: light dark`, so every token has exactly one definition and there is no preprocessor
in the build.

Three colour registers are kept strictly apart, and the naming enforces it:

| Register | Meaning | Rule |
|---|---|---|
| `--science-status-*` | the ordinal ramp of what a mission produced | never used for a data series |
| `--series-*` | the categorical Okabe–Ito palette | never used for a status or a decoration |
| `--accent-*` | interactive and decorative | never used for data |

**Colour is never the only channel.** A series also carries a symbol, a forecast also carries a
dash pattern, and a status also carries its name.

### 2.3 The UI components

The nineteen components the brief requires are there — `Button`, `IconButton`, `Input`, `Select`,
`Tabs`, `Breadcrumbs`, `Card`, `Panel`, `Badge`, `StatusIndicator`, `Tooltip`, `DataTable`,
`MetricCard`, `FilterBar`, `Legend`, `EmptyState`, `LoadingState`, `ErrorState`, `ProvenanceLink` —
each with its states documented and tested: normal, hover, focus, disabled, loading, error.

Their APIs are specialised rather than general. A component with fifty properties would be a
component nobody could read; the contracts are narrow and their names say what they are.

### 2.4 The scientific chart components

Five charts, each a pure function of its typed input and each unit-tested directly.

| Component | What it refuses to do |
|---|---|
| `TimeSeriesChart` | it does not connect across a missing value, and it draws an envelope only when an interval exists |
| `UncertaintyChart` | it draws no band when no uncertainty was given |
| `VerticalProfileChart` | it refuses profiles that do not share a vertical axis — a pressure is not a depth |
| `SpatialMap` | it draws no tile: only TORNE's own layers |
| `CoverageTimeline` | it draws the gaps, the open periods and the unknown ends |

The time axis is a real time axis. Observation, estimation and forecast are separated by a dash
pattern as well as by a colour. The vertical profile keeps the physical nature, the unit and the
reference of its coordinate, and never turns a model level into a distance.

Three of the five are exercised through their exported pure builders — `buildTimeSeriesSeries`,
`buildUncertaintySeries`, `buildCoverageBars` — because jsdom has no canvas to assert on.

### 2.5 The data contracts

`src/types/api/manifest.ts` mirrors the Pydantic schemas field for field, in `snake_case`. One
definition, no drift, and no mapper in which an unknown — a `null` the API takes care to preserve
— could quietly become a zero.

`src/types/visualization/` defines what the charts need and only that: `PointValidity`
(`valid`, `missing`, `invalid`, `out_of_domain`), `MissingReason` (`not_measured`,
`not_yet_published`, `not_attempted`), `QualityStatus` (`declared`, `source_estimated`,
`provisional`, `approved`, `unknown`), `PublicationState` (`established`, `bounded`, `unknown`).
These are the engine's own words. The frontend defines the contract of **representation** of what
the API exposes; it does not define physics.

### 2.6 The Explorer, ported

The legacy features are ported, not redesigned: the status choropleth with its antimeridian
unwrapping, the country, mission, asset, source, model, coverage and result views, and the filters
— which live in the URL, so a filtered map is a shareable link.

### 2.7 The Component Workbench

`/workbench` shows every component, every state and every chart, on **synthetic demo data**, with
a notice that says so at the top of the page. The charts are lazy-loaded, so the workbench does not
pay for a chart the reader has not scrolled to.

---

## 3. The API foundations

### 3.1 The package

The single `explorer/api.py` is now a package — 20 modules, 953 lines:

```text
explorer/api/
  application.py    the composition root: what is assembled, and in what order
  config.py         the settings and the static directory
  errors.py         the error handlers: one shape for every failure
  static.py         the compiled application, and the fallback of a single-page application
  routers/          health, catalogue, missions, assets, sources, models, results
  schemas/          common, catalogue, mission, asset, source, model, result
```

The composition root is called `application.py` and not `app.py`: a submodule named `app` would
shadow the FastAPI instance the package exports.

### 3.2 The version

`/api/v1` is canonical. `/api` answers the same questions, is excluded from the OpenAPI document,
and marks its answers `Deprecation: true` with `Link: </api/v1/...>; rel="successor-version"`. A
consumer that follows the header has migrated itself.

### 3.3 The schemas and the errors

Every route declares its `response_model`, and a test refuses the application if one is missing.
Every failure carries the same envelope:

```json
{
  "detail": "unknown mission 'NOPE'",
  "error": {"code": "not_found", "message": "unknown mission 'NOPE'", "details": null}
}
```

`detail` keeps the field FastAPI has always returned, so a consumer written against the previous
API keeps working unchanged. `error` adds the stable code a new consumer can branch on. The two
never disagree.

### 3.4 The application that also serves the application

`static.py` serves the compiled frontend and answers the browser's direct requests for
`/country/FR`, `/mission/ATMO-001` or `/workbench` with the application itself, which then reads
the path and renders the right view.

The fallback is narrow on purpose:

- a file that exists is served as it is;
- an **API** path is never answered with the application — an unknown endpoint is an error, and
  it is answered as one, in the error envelope;
- a path that names a file is an error too — a missing script must fail as a missing script, not
  as a page;
- anything else is answered with the application.

---

## 4. The boundaries, and how they are held

| Boundary | How it is held |
|---|---|
| the frontend never calls a data provider | the API client speaks to `/api/v1` only; a test scans `frontend/src` for provider strings and CDN strings |
| FastAPI never runs a scientific model | the service reads the catalogue; it computes nothing |
| the scientific layers never import the application | a test refuses the repository if a module outside `explorer/` mentions `fastapi` or `explorer` |
| unknown stays unknown | `null` is preserved end to end; the chart contracts keep a missing value a missing value |
| absence never becomes zero | a missing observation is a break in the series, not a point at zero |

---

## 5. What was measured

**The engine and the API.**

| Check | Result |
|---|---|
| `pytest` | **948 passed** (921 before the mission) |
| `ruff check src/torne/explorer tests/` | All checks passed |
| `ruff format --check src/torne/explorer tests/` | 58 files already formatted |

The repository-wide check also covers `experiments/`, which was clean when the gate ran. Two scripts
of the RESOURCE-002 workstream — `experiments/resource_002_exploration.py` and
`experiments/resource_002_faisabilite_lng.py` — were written concurrently with this mission and
carry lint findings of their own. They are outside this mission's scope and were left untouched.

**The frontend.**

| Check | Result |
|---|---|
| `tsc --noEmit` | exit 0 |
| `eslint .` | 0 problems |
| `vitest run` | 23 files, **114 tests passed** |
| `vite build` | built in 520 ms, 682 modules |
| `playwright test` | **27 tests passed** — 9 journeys on Chromium, Firefox and WebKit |

The browser journeys run against the application FastAPI actually serves — the compiled frontend
in the Python package, not a dev server — and they fail the run on any console error or any
response of 400 or more. They run on the three engines a reader may use: a journey that only
holds on one of them is a journey only half the readers can take.

**The bundle.** The entry chunk is 17.9 kB gzipped; React is 98.1 kB, Leaflet 43.3 kB, and
ECharts — which no page downloads until a chart is shown — is a lazy chunk of 209.4 kB. Each chart
is a chunk of its own, between 1.9 and 2.7 kB gzipped. The whole application is 379.4 kB
gzipped. `scripts/bundle-report.mjs` fails the build if the entry chunk passes 120 kB.

**The frontiers.** Built at build time from `world-atlas` with a Douglas–Peucker simplification of
0.1° and three-decimal rounding: 365 kB, against 739 kB.

---

## 6. Horizon 0 — the limits the mission closed

The mission record listed four things it could not close. They are closed now.

**The map opens an entity with one activation.** The entity list was the
keyboard-reachable equivalent of the map, and it required a double click — a
gesture no keyboard can make. The list now opens an entity on a single
activation, and marks the entity being read with `aria-current`. The map keeps
its two gestures: a click selects, a double click opens. The browser journeys
now open a country from the map's entity list, and from the keyboard.

**The journeys run on three engines.** Chromium, Firefox and WebKit, nine
journeys each: 27 tests, all passing.

**The two dead filters are gone.** The filter bar offered a *Period* and an
*Uncertainty* dropdown, both disabled, both labelled "planned". The API carries
no period and no uncertainty — there is no persisted knowledge record to filter
on — and the overview already said so, in the reader's own words, under
"Planned, not available", driven by the manifest rather than by a hardcoded
label. A dropdown that cannot filter is a promise kept in the wrong place; it
was removed, and its explanation stays where the reader meets it.

**The deprecation of `/api` has a published rule.** The OpenAPI description now
states the canonical prefix, the headers a consumer follows, and on what ground
the legacy prefix goes away: one announced step, once the first application
published outside this repository consumes `/api/v1`, never as a side effect of
another change. A test refuses the application if the rule stops being
published.

---

## 7. What could not be verified

1. **The brief is truncated.** It ends mid-sentence at §13, "Préserver la compatibilité avec les
   routes `/api` actuelles pendant la transition, ou documenter précisément une migration si un
   maintien temporaire est techni…". Everything after §13 — and any third part — is unknown. The
   version choice was made on the part that survived.
2. **The map does not show which entity is being read.** `selectedId` reaches the entity list,
   which marks the current entity, but nothing in the drawing code reads it: the
   `--map-marker-selected` token is computed and never used, and the map never outlines the
   country being read. The status fill is what the choropleth encodes, so the marker must not
   replace it — the outline is the place for it. This was found while closing the keyboard
   affordance and is left as a decision rather than a silent change.
3. **The deferred charts were not written.** Heatmaps, scalar-field maps, scatter plots,
   distributions, correlation matrices, network diagrams and calibration plots were studied and
   left alone, as §6.6 allows. A component is written when its contract and its use are clear.
4. **No application beyond the Explorer was built.** The foundations are exercised by the Explorer
   itself, which is the honest test available before Water Intelligence exists.

---

## 8. The products

| Product | Where |
|---|---|
| the frontend project | `frontend/` |
| the design tokens | `frontend/src/styles/tokens.css` |
| the UI components | `frontend/src/components/ui/`, `frontend/src/components/data/` |
| the scientific charts | `frontend/src/components/visualization/` |
| the data contracts | `frontend/src/types/api/`, `frontend/src/types/visualization/` |
| the ported Explorer | `frontend/src/features/explorer/` |
| the Component Workbench | `frontend/src/features/workbench/`, `frontend/src/dev/` |
| the API package | `src/torne/explorer/api/` |
| the catalogue service | `src/torne/explorer/services/catalogue_service.py` |
| the compiled application | `src/torne/explorer/static/` |
| the API contract tests | `tests/test_explorer_api.py` |
| the browser journeys | `frontend/tests/e2e/explorer.spec.ts` |
| the decisions | `docs/ADR-EXPLORER-FOUNDATIONS-001.md` |
| the programme | `docs/PROGRAMME.md`, `README.md` |
