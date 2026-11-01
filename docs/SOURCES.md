# TORNE — Sources

This document describes the sources TORNE actually queries: what each one gives, what it does not give, and how the
repository uses it. Every adapter is in `src/torne/acquisition/adapters/` and knows **nothing of the domain**: it
builds a URL, says how the source is walked, returns the next page or `None`, and verifies the response it received
against what it asked.

**Rule of evidence.** Each statement below was **observed on the network** at the date given, unless it is marked
*inference* or *not verified*. A source that is studied but not queried by an adapter is not in this document.

The qualification of economic sources for objective B (Mississippi barge freight, grain movements, locks) is deferred
and kept in history: `git show 0fc3ad9:docs/SOURCES.md`, Part II (`docs/PROGRAMME.md` §9).

**Summary**

| Source | Modality | Adapter | Publication class (§3.11) | Main limit |
|---|---|---|---|---|
| Hub'EAU v2 `observations_tr` | discharge and stage, France | `hubeau`, `hubeau_feed` | not established | station and window filters are ignored; Q is computed from H |
| USGS OGC API | discharge, United States | `usgs_ogc` | not established | — |
| USGS Water Services (decommissioned) | discharge, United States | `usgs` | not established | shut down on 2027-02-22 |
| Copernicus Data Space OData | satellite product catalogue | `copernicus` | not established | no licence per product |
| Copernicus Data Space STAC | surface observation (soil moisture, vegetation, snow, water level) | `copernicus_stac` | **P** (each item carries `published`) | assets require OIDC authentication; no unit published |
| GHCN-Daily (NOAA/NCEI) | station temperature and precipitation | `ghcnd` | **N** (no publication date per value) | always returns the period of record; French values are redistributed from ECA&D |
| Météo-France observation API | station observations, France | `meteofrance` | not established | OAuth2 token required |

---

## 1. Hub'EAU v2 — real-time hydrometry (France)

| | |
|---|---|
| Source identifier | `hubeau.hydrometrie.observations_tr` |
| Access point | `https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr` |
| Pagination | **cursor**: `next` is an absolute URL carrying a signed seek key |
| Exhaustiveness | declared when the source returns `next: null` |

### 1.1 What the instance does with filters

**Verified on 2026-10-31, then on 2026-11-01 on the rows returned (not only on `count`):**

| Probe | Result |
|---|---|
| `code_station=O919001001` | **ignored** — the page returns rows of `A402061001`, `A405062001`, `P846251001`; `count` is the collection's |
| `code_station=ZZZZZZZZZZ` (non-existent) | **ignored** — same rows, same `count` |
| `date_debut` + `date_fin` (2020–2021) | **ignored** — the rows are the most recent instants of the day |
| `station`, `codeStation`, `station_code`, `codes_station` | **ignored**, like `code_station` |
| `date_obs`, `date_obs_start`, `debut`, `start_date` | **ignored**, like `date_debut` |
| `code_cours_eau` | **ignored** |
| `grandeur_hydro` | **applied** — rows of a `Q` page all carry `Q`, those of an `H` page all carry `H` |
| `code_statut` | **applied** — `code_statut=1` returns an empty page, while rows carry `4` |
| `page` | accepted, **ignored** — `page=2` returns the page of `page=1` |
| `index` | accepted, **ignored** — every offset returns the first page |
| `size` | honoured up to **10 000**; 50 000 is refused with a 400 |
| `format` | `json` and `geojson` work; `csv` and `xml` are refused with a 400 |

The filters are nevertheless **echoed** in the `first`/`next` links. A filter echoed in a URL is not evidence of
filtering (INV-37).

**The pagination is a signed seek key.** The `next` cursor decodes to `\x02` + eight framing bytes + `0x3f 0x0a` +
`code_site_code_station_grandeur_date_obs`. The framing is validated: a zeroed framing is refused with a **500**, and a
forged date inside a valid framing is accepted but **ignored**. The collection can only be walked from its beginning.

**The order is reverse chronological.** The first page holds the most recent instants, stations are interleaved inside
each five-minute slice, and one station's rows are spread over the whole collection.

**The instance throttles.** It answers **503** when asked too much too quickly: 8 pages of 10 000 rows in a row trigger
it, while 25 pages of 2 000 rows one second apart go through. The socle's retry policy, widened, rides it out.

### 1.2 How the repository uses it

Two adapters ask two different questions:

- `hubeau` — *the observations of these stations*. Its conformity predicate checks the identifiers **in the rows
  received**; on this instance it renders `non_conforme` and the acquisition is blocked, while the raw evidence is kept.
- `hubeau_feed` — *every observation of one quantity*. It asks for no station and no window, so it asks only what the
  source can answer, and verifies on the rows that they carry the requested quantity.

Selecting a station inside the acquired feed is a **declared, verified transformation** (`torne.hydrology.hubeau`),
not a filter the provider is trusted to apply: every selected row is checked to carry the station's code.

### 1.3 What the rows carry, and two facts a consumer must know

Each row carries the observation's coordinates, the site code, the vertical datum, the series window, the method, the
qualification, the status and the continuity. It carries **no unit**: the discharge unit is declared by the
interpretation layer (a *débit* is in cubic metres per second by definition), and the **height unit is left
undeclared**, because this source says nothing about it.

- **Half of the discharge rows carry no station code.** They keep the site code, coordinates and value, and duplicate
  rows that do carry a station code (26 369 of 26 653 such rows matched a station row on `(code_site, date_obs)`, and
  25 996 of them carried the identical value).
- **Discharge rows carry two declared methods**: `Calculée` (computed from the height) and `Mesurée`. Height rows carry
  `Mesurée`. The published discharge is therefore, by the agency's own statement, mostly a function of the published
  height: the two are **not independent evidence**. HYDRO-001 tests that statement
  (`docs/PRE-REGISTRATION-HYDRO-001.md`).

---

## 2. USGS — "Water Data for the Nation", OGC API (United States)

| | |
|---|---|
| Source identifier | `usgs.ogc.<collection>` |
| Access point | `https://api.waterdata.usgs.gov/ogcapi/v1/collections/<collection>/items` |
| Pagination | **cursor**: an absolute `next` link that already carries every filter of the request |
| Exhaustiveness | **declared**: the end of the walk is the absence of `next` |
| API key | optional (`api_key` parameter or `X-Api-Key` header), carried by `credential_ref` — never in the recorded request |

**Verified on 2026-11-01:**

- collections are `continuous`, `daily`, `time-series-metadata`, `monitoring-locations` and `peaks`; joins use
  `monitoring_location_id`, of the form `<agency>-<number>` — `USGS-05587450`, never `05587450`;
- the `next` link is absolute and carries every filter: the adapter follows it **as is**. Rebuilding the request by
  hand is how a walk silently changes its question;
- `limit` is capped at 50 000 (10 by default): a year of 15-minute values fits in one response of about 23 MB;
- **without an explicit `datetime` window**, the server returns about **one year** of continuous values, so the window
  is never left implicit;
- `value` is always a **string**; `daily.time` is a bare date (`2024-01-03`) and `continuous.time` an ISO 8601 instant
  with explicit offset;
- records are **not sorted** by time: chronology is established by the semantic layer;
- any undeclared query parameter is refused (400);
- the anonymous quota is 1 000 requests per hour, and quota headers only appear on the 429;
- **site statistics** are not in the OGC API but in a separate beta service
  (`https://api.waterdata.usgs.gov/statistics/v0/observationNormals`, paginated by `next_token`). It provided the
  independent reference of mission 002.

**How the repository uses it.** The adapter checks station, parameters and useful fields on the records received, and
renders `conforme`, `non_conforme` or `indeterminate` — never "conforming" by default.

### 2.1 USGS Water Services (decommissioned)

| | |
|---|---|
| Source identifier | `usgs.nwis.iv` |
| Access point | `https://waterservices.usgs.gov/nwis/iv/` |
| Pagination | none: the requested window fits in one response |
| Exhaustiveness | `undeclared` |

Water Services is decommissioned: packets degrade from **2027-02-01**, shutdown on **2027-02-22**. The adapter stays for
the record; new work uses the OGC API. Verified on 2026-10-31: JSON only with `format=json`; `sites`, `parameterCd`,
`period`, `startDT`, `endDT` are echoed and confirmed in `queryInfo.criteria`; recent values are marked provisional
(`P`), and that marker is kept in the raw evidence.

---

## 3. Copernicus Data Space

### 3.1 OData product catalogue

| | |
|---|---|
| Source identifier | `copernicus.dataspace.products` |
| Access point | `https://catalogue.dataspace.copernicus.eu/odata/v1/Products` |
| Pagination | OData v4: `$top` and `$skip` |
| Exhaustiveness | declared when `@odata.nextLink` is absent |

Verified on 2026-10-31: products under `value`, `@odata.nextLink` absolute with encoded parameters (`%24top`,
`%24filter`, `%24skip`) that the adapter decodes and carries into the next request; pagination and filters are applied;
no licence is published per product.

### 3.2 STAC catalogue of surface observations

| | |
|---|---|
| Source identifier | `copernicus.dataspace.stac` |
| Access point | `https://stac.dataspace.copernicus.eu/v1/search` |
| Pagination | an absolute `next` link carrying a `token`; its disappearance is the only declaration of exhaustion (no `numberMatched`) |
| Publication class | **P**: every item carries `published`, distinct from `datetime` (validity) and from `created` / `updated` (catalogue entry) |

**Verified on 2026-11-01:**

- STAC 1.1.0 (OGC API – Features); 428 collections, including the Copernicus Land Monitoring Service surface products
  absent from the OData catalogue;
- `datetime` requires full RFC 3339 (`2023-01-01/2023-12-31` is refused; `2023-01-01T00:00:00Z/…` is accepted);
- spatial and temporal filters **are applied**, and the predicate still verifies collection, footprint and window on
  the items received; an empty page is a complete answer ("there is none");
- a non-existent collection is refused with a 400;
- the catalogue publishes **no unit** on bands (`swi010`, `ssm`, `et_std`, `lai`, `ndvi`); units in the registry are
  producer declarations, marked `unit_established=False`;
- data assets carry `auth:refs`: downloading pixels requires OIDC authentication, so the repository reads metadata and
  grids, not pixel values.

**Registry and dependence.** `src/torne/eo/products.py` records 13 collections with their coverage and their
**meteorological dependence** (`INDEPENDENT`, `DEPENDENT`, `NOT_AUDITED`). Facts that matter for a reconstruction:

| Collection | Coverage | Dependence | Note |
|---|---|---|---|
| SSM 1 km daily (Sentinel-1) | 2014-10 → open | independent | radar retrieval with a noise band |
| SWI 1 km daily V1 / V2 | 2014-12 → 2025-07 / 2025-07 → open | not audited | an index over 2–100-day windows; V1 1.0.2 for 2023 days was published on 2025-03-26 |
| Evapotranspiration 300 m 10-daily | **2025-11-01 → open** | not audited | covers no historical year; a model output with gap filling |
| LAI, FAPAR 300 m 10-daily | 2013-10 → 2026-02 | independent | optical |
| NDVI 300 m 10-daily | 2014-01 → **2021-01** | independent | stopped in 2021 |
| Water level (rivers, altimetry) | 2008-07 → open | independent | a level, not a discharge; the observation date is inside the GeoJSON, not in the item `datetime` |
| Sentinel-1 GRD, Sentinel-2 L2A | 2014-10 / 2015-06 → open | independent | published about one hour after acquisition; Sentinel-2 rasters are in UTM while footprints are in EPSG:4326 |

---

## 4. GHCN-Daily (NOAA/NCEI)

| | |
|---|---|
| Source identifier | `noaa.ghcnd.daily` |
| Access point | `…/global-historical-climatology-network-daily/access/{station}.csv` |
| Version | 3.35-upd-2026103017 (`ghcnd-version.txt`) |
| Access | no account, no secret |
| Publication class | **N**: no publication date per value; every observation is read with `PublicationState.UNKNOWN`, so `usable_at` is `None`. The class is established (ATMO-001) but not yet recorded in the adapter's `Source.publication_class` |

**Verified on 2026-11-01:**

- 109 French stations in `ghcnd-stations.txt`; no coordinate datum is published (declared absent, not assumed WGS 84);
- **the access point always returns the period of record**: a request for 2015–2025 returned 1944–2026 and was refused
  as non-conforming. The adapter therefore promises no window; the window is a filter applied after acquisition;
- units are carried by (element, measurement), not by the source: `TMAX` tenths of °C, `PRCP` tenths of mm, `ASLP`
  tenths of hPa (`readme.txt` v3.35);
- dates are civil dates with no time zone: the zone is an argument of the reading, and instants are the start of the
  local civil day;
- conformity (`station`, `elements`) is verified **on the body received**: an HTML page served with a 200 makes no
  criterion verifiable and produces an abstention, never an agreement;
- **provenance for France is ECA&D, not Météo-France**: source flag `E` at Lille, Toulouse and Marseille; GSOD (`S`) then
  `2` at Paris-Montsouris. The link ECA&D → Météo-France is not established by any metadata read;
- quality flags: 0.3–0.9 % of values carry a failed-check flag (`I`, `O`). They are kept with their flag and the status
  `UNKNOWN`, because the closed vocabulary has no "measured, failed a check" state (deferred A1). Precipitation
  aggregation is not homogeneous (`B`, `D`, `H` measurement flags at Paris);
- coverage: Lille 1944–2026 complete; Toulouse 1947–2026 complete; Marseille 1921–2026 with a 793-day gap (1943-07 →
  1945-08); Paris-Montsouris 1983–2026 at 62.4 %, with a 2 638-day gap (1992-01 → 1999-03).

---

## 5. Météo-France observation API

| | |
|---|---|
| Source identifier | `meteofrance.observation` |
| Access point | `public-api.meteofrance.fr/public/DPPaquetObs/…` |
| Access | **OAuth2 token**, held by reference (`meteofrance.oauth2`, environment variable `METEOFRANCE_TOKEN` or a git-ignored `.env`) |

**Verified on 2026-11-01, without a token:** the three documented routes answer `401` (`"Missing Credentials"`; the
climatology service answers `you must provide a token`); the former `DPPaquetV1/…` path answers `404`;
`donnees.meteofrance.fr` does not resolve from the development machine. The adapter classifies the failure as
`authentication` and interprets nothing; the journal records the credential reference, never a value.

The body of the refusal (where the source explains the expected header) is **not kept** as evidence: a `4xx` is an
acquisition failure and the socle keeps status and content type only (deferred A9).

**Not verified:** the data itself, the token lifetime, and whether a refresh token is needed.

Open Météo-France datasets on `data.gouv.fr` (digitised daily observation records and monthly climatological tables)
are **scanned images and an archive inventory**, not structured data, and are not used.

---

## 6. What all sources share

What the socle guarantees, whatever the source:

- a successful response is **not** evidence that the provider returned everything it had;
- the presence of raw data is **not** semantic conformity;
- a source that answers beside the question produces a `non_conforme` outcome and **no observation**, and its raw
  evidence is kept anyway;
- a source whose publication class is not established by execution produces no observation admitted in a
  point-in-time reconstruction.

**What is still missing.** The publication class is established for two sources only: Copernicus STAC (P, recorded in
its `Source`) and GHCN-Daily (N, carried by each observation's publication state). For the others it is **not
established**, and their observations are not admitted in point-in-time reconstruction until it is.
