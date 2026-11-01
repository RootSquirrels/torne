// TORNE Explorer — map front end. It reads /api/manifest and nothing else:
// no computation, no call to a data provider. Every fact and status is shown
// with the references that support it.

const WORLD_TOPOJSON = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json";
const EUROPE_BOUNDS = [[35, -12], [70, 35]];
const EUROPE_CENTER = [52, 10];
const EUROPE_ZOOM = 4;

// ISO 3166-1 alpha-2 -> numeric, as used by world-atlas feature ids.
const ISO_NUMERIC = {
  AL: "008", AT: "040", BE: "056", BA: "070", BG: "100", BY: "112", CH: "756", CY: "196",
  CZ: "203", DE: "276", DK: "208", EE: "233", ES: "724", FI: "246", FR: "250", GB: "826",
  GR: "300", HR: "191", HU: "348", IE: "372", IS: "352", IT: "380", LT: "440", LU: "442",
  LV: "428", MD: "498", ME: "499", MK: "807", MT: "470", NL: "528", NO: "578", PL: "616",
  PT: "620", RO: "642", RS: "688", SE: "752", SI: "705", SK: "703", UA: "804", US: "840",
};
const NUMERIC_ISO = Object.fromEntries(Object.entries(ISO_NUMERIC).map(([a, n]) => [n, a]));

const state = { manifest: null, filters: { domain: "", status: "", kind: "" }, country: null, view: null };
const names = {};
let map;
let countryLayer;
let assetLayer;

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const statusRank = (label) => state.manifest.statuses.find((s) => s.status === label)?.rank ?? 0;

const byId = (section, key, value) => state.manifest[section].find((item) => item[key] === value);

const domainTitle = (id) => byId("domains", "domain_id", id)?.title ?? id;

const countryName = (code) => names[code] ?? code;

const badge = (label) => {
  const rank = label ? statusRank(label) : 0;
  return `<span class="badge s${rank}">${escapeHtml(label ?? "not covered")}</span>`;
};

const link = (action, id, text) =>
  `<button class="link" type="button" data-action="${action}" data-id="${escapeHtml(id)}">${escapeHtml(text)}</button>`;

// A reference chip: documents and scripts link to the repository; missions open
// in the explorer; implementations show the importable name.
function refChip(ref) {
  if (ref.kind === "mission") return `<span class="ref">${link("mission", ref.target, ref.target)}</span>`;
  if (ref.url) {
    return `<a class="ref" href="${escapeHtml(ref.url)}" target="_blank" rel="noopener">${escapeHtml(ref.target)}</a>`;
  }
  return `<span class="ref" title="${escapeHtml(ref.kind)}">${escapeHtml(ref.target)}</span>`;
}

const refs = (list) => `<span class="refs">${list.map(refChip).join("")}</span>`;

const factList = (facts, empty = "Nothing recorded.") =>
  facts.length
    ? facts.map((f) => `<div class="fact"><p>${escapeHtml(f.text)}</p>${refs(f.refs)}</div>`).join("")
    : `<p class="muted">${escapeHtml(empty)}</p>`;

// ----------------------------------------------------------------- filtering

function missionMatches(mission) {
  const { domain, status } = state.filters;
  if (domain && !mission.domain_ids.includes(domain)) return false;
  if (status && mission.status_rank < statusRank(status)) return false;
  return true;
}

function assetMatches(asset) {
  const { domain, kind } = state.filters;
  if (domain && asset.domain_id !== domain) return false;
  if (kind && asset.kind !== kind) return false;
  const missions = state.manifest.missions.filter((m) => asset.mission_ids.includes(m.mission_id));
  return missions.length === 0 || missions.some(missionMatches);
}

function countryRank(code) {
  const ranks = state.manifest.missions
    .filter((m) => m.countries.includes(code) && missionMatches(m))
    .map((m) => m.status_rank);
  return ranks.length ? Math.max(...ranks) : 0;
}

// ----------------------------------------------------------------------- map

function styleCountry(feature) {
  const code = NUMERIC_ISO[feature.id];
  const rank = code ? countryRank(code) : 0;
  const selected = code && code === state.country;
  return {
    color: selected ? cssVar("--ink") : cssVar("--land-line"),
    weight: selected ? 2 : 0.6,
    fillColor: cssVar(`--status-${rank}`),
    fillOpacity: 1,
  };
}

function drawAssets() {
  if (!assetLayer) return;
  assetLayer.clearLayers();
  for (const asset of state.manifest.assets.filter(assetMatches)) {
    if (asset.kind === "station" && asset.point) {
      const [lon, lat] = asset.point;
      L.circleMarker([lat, lon], {
        radius: 6,
        color: cssVar("--surface"),
        weight: 1.5,
        fillColor: cssVar("--marker"),
        fillOpacity: 1,
      })
        .bindTooltip(`${escapeHtml(asset.name)} · ${escapeHtml(asset.asset_id)}`)
        .on("click", () => navigate({ view: "asset", id: asset.asset_id }))
        .addTo(assetLayer);
    }
  }
}

function refreshMap() {
  if (!map) return;
  map.invalidateSize({ animate: false });
  countryLayer?.setStyle(styleCountry);
  drawAssets();
}

// A ring that crosses the antimeridian (Russia, Fiji) spans more than 180° of
// longitude and Leaflet draws it across the whole map; shift its western
// points by 360° so it stays one shape.
function unwrapAntimeridian(geometry) {
  const fixRing = (ring) => {
    const lons = ring.map(([lon]) => lon);
    if (Math.max(...lons) - Math.min(...lons) <= 180) return ring;
    return ring.map(([lon, lat]) => [lon < 0 ? lon + 360 : lon, lat]);
  };
  if (geometry?.type === "Polygon") geometry.coordinates = geometry.coordinates.map(fixRing);
  if (geometry?.type === "MultiPolygon") {
    geometry.coordinates = geometry.coordinates.map((polygon) => polygon.map(fixRing));
  }
  return geometry;
}

// Until the user moves the map, every resize re-fits Europe: the container can
// reach its final size after the first fit, and a fit on a narrow container
// would leave the whole world in view. Any drag, wheel or zoom click hands the
// view to the user; the Europe button takes it back.
let followEurope = true;

function showEurope() {
  followEurope = true;
  map.invalidateSize({ animate: false });
  map.fitBounds(EUROPE_BOUNDS, { animate: false });
}

function handOverView() {
  followEurope = false;
}

async function initMap() {
  // Europe is the initial viewport; zoom and pan stay free.
  map = L.map("map", { center: EUROPE_CENTER, zoom: EUROPE_ZOOM, zoomSnap: 0.25, minZoom: 2, worldCopyJump: true });
  map.attributionControl.setPrefix(false).addAttribution("Boundaries: Natural Earth via world-atlas");

  const EuropeControl = L.Control.extend({
    options: { position: "topleft" },
    onAdd() {
      const button = L.DomUtil.create("button", "map-button");
      button.type = "button";
      button.textContent = "Europe";
      button.title = "Return to the Europe view";
      L.DomEvent.on(button, "click", (event) => {
        L.DomEvent.stop(event);
        showEurope();
      });
      return button;
    },
  });
  map.addControl(new EuropeControl());
  assetLayer = L.layerGroup();

  const world = await fetch(WORLD_TOPOJSON).then((r) => r.json());
  const countries = topojson.feature(world, world.objects.countries);
  for (const feature of countries.features) {
    unwrapAntimeridian(feature.geometry);
    const code = NUMERIC_ISO[feature.id];
    if (code) names[code] = feature.properties?.name ?? code;
  }
  countryLayer = L.geoJSON(countries, {
    style: styleCountry,
    onEachFeature: (feature, layer) => {
      const name = feature.properties?.name ?? "";
      layer.bindTooltip(escapeHtml(name), { sticky: true });
      layer.on("click", () => {
        const code = NUMERIC_ISO[feature.id];
        navigate(code ? { view: "country", id: code } : { view: "uncovered", id: name });
      });
    },
  }).addTo(map);
  assetLayer.addTo(map);
  drawAssets();
  // The first fit can run before the grid layout settles; refit once it has,
  // and keep the size right when the window changes.
  map.on("dragstart", handOverView);
  const container = map.getContainer();
  container.addEventListener("wheel", handOverView, { passive: true });
  container.querySelector(".leaflet-control-zoom")?.addEventListener("click", handOverView);
  // Leaflet fires `resize` whenever invalidateSize finds a new size: that is
  // the single place where the Europe view is re-fitted.
  map.on("resize", () => {
    if (followEurope) map.fitBounds(EUROPE_BOUNDS, { animate: false });
  });
  const remeasure = () => map.invalidateSize({ animate: false });
  new ResizeObserver(remeasure).observe(container);
  window.addEventListener("resize", remeasure);
  document.addEventListener("visibilitychange", remeasure);
  showEurope();
  render();
}

// ---------------------------------------------------------------- navigation

const panel = () => document.getElementById("panel");

function navigate(view) {
  state.view = view;
  state.country = view.view === "country" || view.view === "domain" ? view.country ?? view.id : state.country;
  if (view.view === "overview") state.country = null;
  render();
}

function crumbs(items) {
  const parts = [`${link("overview", "", "Europe")}`, ...items];
  return `<nav class="crumbs" aria-label="Breadcrumb">${parts.join('<span class="sep">›</span>')}</nav>`;
}

function bindPanelActions() {
  panel().querySelectorAll("button[data-action]").forEach((el) => {
    el.addEventListener("click", () => {
      const { action, id, country } = el.dataset;
      if (action === "overview") navigate({ view: "overview" });
      else if (action === "domain") navigate({ view: "domain", country, id });
      else navigate({ view: action, id });
    });
  });
}

function render() {
  refreshMap();
  const view = state.view ?? { view: "overview" };
  const renderers = {
    overview: renderOverview,
    uncovered: renderUncovered,
    country: renderCountry,
    domain: renderDomain,
    mission: renderMission,
    asset: renderAsset,
    source: renderSource,
    model: renderModel,
    coverage: renderCoverage,
    results: renderResults,
  };
  panel().innerHTML = (renderers[view.view] ?? renderOverview)(view);
  panel().scrollTop = 0;
  bindPanelActions();
}

// --------------------------------------------------------------------- views

function resultsSummary() {
  const results = state.manifest.results;
  if (results.persisted.length) return `<p>${results.persisted.length} persisted record(s).</p>`;
  return `<p class="gap">${escapeHtml(results.gap)}</p>`;
}

function renderOverview() {
  const countries = state.manifest.countries
    .map((c) => {
      const best = Math.max(...c.domains.map((d) => d.status_rank));
      const label = state.manifest.statuses.find((s) => s.rank === best)?.status;
      return `<div class="row">${link("country", c.country, countryName(c.country))}${badge(label)}</div>`;
    })
    .join("");
  const regions = state.manifest.regions
    .map(
      (r) => `<div class="row"><span>${escapeHtml(r.region)}-wide · ${escapeHtml(r.domain_ids.map(domainTitle).join(", "))}</span>${badge(r.status)}</div>
      <p class="muted small">From ${r.mission_ids.map((id) => link("mission", id, id)).join(", ")}</p>`,
    )
    .join("");
  const executed = state.manifest.models.filter((m) => m.executed_on_real_data).length;
  return `${crumbs([])}
    <h2>Europe</h2>
    <p class="muted">Colours show the highest status a country's missions have reached — earned by evidence, never declared. Select a country, or explore a concept below.</p>
    <h3>Countries with missions</h3>${countries}
    <h3>Region-wide coverage</h3>${regions}
    <h3>Concepts</h3>
    <div class="row">${link("coverage", "", "Observation coverage")}<span class="muted">${state.manifest.coverage.length} periods</span></div>
    <div class="row">${link("model", "", "Models and methods")}<span class="muted">${executed} of ${state.manifest.models.length} run on real data</span></div>
    <div class="row">${link("results", "", "Published results")}<span class="muted">${state.manifest.results.persisted.length} persisted</span></div>
    <h3>Planned, not available</h3>
    ${state.manifest.planned.map((p) => `<p class="muted small">${escapeHtml(p.feature)} — needs ${escapeHtml(p.needs)}</p>`).join("")}`;
}

function renderUncovered(view) {
  return `${crumbs([escapeHtml(view.id)])}<h2>${escapeHtml(view.id)}</h2>
    <p class="muted">No mission has touched this country. Region-wide surface products may cover it; that coverage is not a national status.</p>`;
}

function renderCountry(view) {
  const code = view.id;
  const summary = state.manifest.countries.find((c) => c.country === code);
  if (!summary) return renderUncovered({ id: countryName(code) });
  const domains = summary.domains
    .filter((d) => !state.filters.domain || d.domain_id === state.filters.domain)
    .map(
      (d) => `<div class="row">
        <button class="link" type="button" data-action="domain" data-country="${escapeHtml(code)}" data-id="${escapeHtml(d.domain_id)}">${escapeHtml(d.title)}</button>
        ${badge(d.status)}</div>
        ${d.status ? `<p class="muted small">Status from ${d.status_from.map((id) => link("mission", id, id)).join(", ")}</p>` : ""}`,
    )
    .join("");
  const regional = state.manifest.regions
    .map((r) => `<div class="row"><span>${escapeHtml(r.region)}-wide · ${escapeHtml(r.domain_ids.map(domainTitle).join(", "))}</span>${badge(r.status)}</div>`)
    .join("");
  return `${crumbs([escapeHtml(countryName(code))])}
    <h2>${escapeHtml(countryName(code))}</h2>
    <h3>Domains</h3>${domains}
    <h3>Region-wide, not national</h3>${regional}
    <h3>Published results</h3>${resultsSummary()}`;
}

function renderDomain(view) {
  const code = view.country;
  const summary = state.manifest.countries.find((c) => c.country === code);
  const d = summary?.domains.find((x) => x.domain_id === view.id);
  if (!d) return renderCountry({ id: code });
  const missions = d.mission_ids.map((id) => byId("missions", "mission_id", id)).filter(missionMatches);
  const assets = d.asset_ids.map((id) => byId("assets", "asset_id", id)).filter(assetMatches);
  const coverage = state.manifest.coverage.filter((c) => c.country === code && c.domain_id === d.domain_id);
  return `${crumbs([link("country", code, countryName(code)), escapeHtml(d.title)])}
    <h2>${escapeHtml(d.title)} · ${escapeHtml(countryName(code))}</h2>${badge(d.status)}
    <h3>Missions</h3>${missions.map((m) => `<div class="row">${link("mission", m.mission_id, m.mission_id)}${badge(m.status)}</div><p class="muted small">${escapeHtml(m.title)}</p>`).join("") || '<p class="muted">None matches the filters.</p>'}
    <h3>Sources</h3>${d.source_ids.map((id) => `<div class="row">${link("source", id, byId("sources", "source_id", id)?.title ?? id)}</div>`).join("") || '<p class="muted">None.</p>'}
    <h3>Physical assets</h3>${assets.map((a) => `<div class="row">${link("asset", a.asset_id, a.name)}<span class="muted">${escapeHtml(a.kind)}</span></div>`).join("") || '<p class="muted">None touched yet.</p>'}
    <h3>Observation coverage</h3>${coverageBars(coverage) || '<p class="muted">No measured period.</p>'}
    <h3>Models and methods</h3>${d.model_keys.map((k) => modelRow(byId("models", "key", k))).join("") || '<p class="muted">None.</p>'}
    <h3>Published results</h3>${resultsSummary()}`;
}

function modelRow(m) {
  const state_ = m.executed_on_real_data ? "run on real data" : "implemented, not run on real data";
  return `<div class="row">${link("model", m.key, m.title)}<span class="muted small">${escapeHtml(state_)}</span></div>`;
}

function renderMission(view) {
  const m = byId("missions", "mission_id", view.id);
  if (!m) return renderOverview();
  const country = m.countries[0];
  const trail = country ? [link("country", country, countryName(country))] : [];
  return `${crumbs([...trail, escapeHtml(m.mission_id)])}
    <h2>${escapeHtml(m.mission_id)}</h2>${badge(m.status)}
    <p>${escapeHtml(m.title)}</p>
    <p class="muted small">Status supported by</p>${refs(m.status_basis)}
    <h3>Question</h3><p>${escapeHtml(m.question)}</p>
    <h3>Produced</h3>${factList(m.produced)}
    <h3>Not established</h3>${factList(m.not_established)}
    <h3>Sources</h3>${m.source_ids.map((id) => `<div class="row">${link("source", id, byId("sources", "source_id", id)?.title ?? id)}</div>`).join("") || '<p class="muted">None.</p>'}
    <h3>Physical assets</h3>${m.asset_ids.map((id) => `<div class="row">${link("asset", id, byId("assets", "asset_id", id)?.name ?? id)}</div>`).join("") || '<p class="muted">None touched.</p>'}
    <h3>Models and methods</h3>${m.model_keys.map((k) => modelRow(byId("models", "key", k))).join("") || '<p class="muted">None.</p>'}
    ${m.domain_ids.includes("earth_observation") ? `<h3>Observation coverage</h3>${link("coverage", "", "Surface product coverage")}` : ""}`;
}

function renderAsset(view) {
  const a = byId("assets", "asset_id", view.id);
  if (!a) return renderOverview();
  if (a.point && map) {
    handOverView();
    map.setView([a.point[1], a.point[0]], Math.max(map.getZoom(), 6));
  }
  const source = byId("sources", "source_id", a.source_id);
  const coverage = state.manifest.coverage.filter((c) => c.subject_id === a.asset_id);
  const trail = a.country
    ? [link("country", a.country, countryName(a.country)), `<button class="link" type="button" data-action="domain" data-country="${escapeHtml(a.country)}" data-id="${escapeHtml(a.domain_id)}">${escapeHtml(domainTitle(a.domain_id))}</button>`]
    : [];
  return `${crumbs([...trail, escapeHtml(a.name)])}
    <h2>${escapeHtml(a.name)}</h2>
    <p class="muted">${escapeHtml(a.kind)} · ${escapeHtml(a.asset_id)}</p>
    <div class="card"><dl>
      <dt>Source</dt><dd>${link("source", a.source_id, source?.title ?? a.source_id)}</dd>
      <dt>Location</dt><dd>${escapeHtml(a.point ? `${a.point[1].toFixed(4)}, ${a.point[0].toFixed(4)}` : "—")} ${refs([a.location_ref])}</dd>
    </dl></div>
    <h3>Observation coverage</h3>${coverageBars(coverage) || '<p class="muted">Not measured.</p>'}
    <h3>What was measured</h3>${factList(a.facts)}
    <h3>Missions</h3>${a.mission_ids.map((id) => `<div class="row">${link("mission", id, id)}${badge(byId("missions", "mission_id", id).status)}</div>`).join("")}`;
}

function renderSource(view) {
  const s = byId("sources", "source_id", view.id);
  if (!s) return renderOverview();
  return `${crumbs([escapeHtml(s.title)])}
    <h2>${escapeHtml(s.title)}</h2>
    <p class="muted">${escapeHtml(s.source_id)} · ${escapeHtml(domainTitle(s.domain_id))}</p>
    <div class="card"><dl>
      <dt>Publication class</dt><dd>${escapeHtml(s.publication_class?.toUpperCase() ?? "not established")}</dd>
      <dt>Adapter</dt><dd>${refs([s.adapter_ref])}</dd>
      <dt>Qualified in</dt><dd>${refs([s.qualified_in])}</dd>
    </dl></div>
    <h3>Established behaviour</h3>${factList(s.facts)}
    <h3>Used by</h3>${s.mission_ids.map((id) => `<div class="row">${link("mission", id, id)}</div>`).join("") || '<p class="muted">No mission.</p>'}`;
}

function renderModel(view) {
  if (!view.id) {
    const rows = state.manifest.models
      .map((m) => `${modelRow(m)}<p class="muted small">${escapeHtml(m.kind)}</p>`)
      .join("");
    return `${crumbs(["Models and methods"])}<h2>Models and methods</h2>
      <p class="muted">Identities and versions are read from the code. "Run on real data" requires recorded evidence.</p>${rows}`;
  }
  const m = byId("models", "key", view.id);
  if (!m) return renderModel({});
  return `${crumbs([link("model", "", "Models and methods"), escapeHtml(m.title)])}
    <h2>${escapeHtml(m.title)}</h2>
    <p class="muted">${escapeHtml(m.kind)}</p>
    <div class="card"><dl>
      <dt>Identity</dt><dd>${escapeHtml(m.identity)} ${refs([m.identity_ref])}</dd>
      <dt>Version</dt><dd>${escapeHtml(m.version ?? "not exposed by the module")} ${m.version_ref ? refs([m.version_ref]) : ""}</dd>
    </dl></div>
    <h3>Runs on real data</h3>${factList(m.runs, "Implemented and tested; never run on real data.")}
    <h3>Missions</h3>${m.mission_ids.map((id) => `<div class="row">${link("mission", id, id)}</div>`).join("") || '<p class="muted">No mission.</p>'}`;
}

function coverageBars(entries) {
  if (!entries.length) return "";
  const year = (iso) => (iso ? Number(String(iso).slice(0, 4)) : null);
  const now = new Date().getUTCFullYear();
  const starts = entries.map((e) => year(e.start)).filter(Boolean);
  const min = Math.min(...starts, now - 10);
  const span = Math.max(now + 1 - min, 1);
  return entries
    .map((e) => {
      const s = year(e.start) ?? min;
      const end = e.open ? now + 1 : (year(e.end) ?? now) + 1;
      const left = ((s - min) / span) * 100;
      const width = Math.max(((end - s) / span) * 100, 1);
      return `<div class="cov">
        <div class="cov-label"><span>${escapeHtml(e.title)}</span><span class="muted small">${escapeHtml(String(e.start).slice(0, 10))} → ${escapeHtml(e.open ? "open" : String(e.end).slice(0, 10))}</span></div>
        <div class="cov-track"><div class="cov-bar" style="left:${left}%;width:${width}%"></div></div>
        ${refs(e.refs)}</div>`;
    })
    .join("") + `<p class="muted small">Axis ${min} → ${now}</p>`;
}

function renderCoverage() {
  const filtered = state.manifest.coverage.filter((c) => !state.filters.domain || c.domain_id === state.filters.domain);
  const assets = filtered.filter((c) => c.subject_kind === "asset");
  const products = filtered.filter((c) => c.subject_kind === "surface_product");
  return `${crumbs(["Observation coverage"])}
    <h2>Observation coverage</h2>
    <p class="muted">Periods that observations cover — not periods for which knowledge was produced.</p>
    <h3>Stations</h3>${coverageBars(assets) || '<p class="muted">None matches the filters.</p>'}
    <h3>Surface products (Europe-wide)</h3>${coverageBars(products) || '<p class="muted">None matches the filters.</p>'}`;
}

function renderResults() {
  const r = state.manifest.results;
  const runs = r.runs_not_persisted
    .map((run) => `<div class="card"><div class="row">${link("mission", run.mission_id, run.mission_id)}${badge(run.status)}</div>${factList(run.produced)}</div>`)
    .join("");
  return `${crumbs(["Published results"])}
    <h2>Published results</h2>
    ${resultsSummary()}
    <h3>Produced in a run, not persisted</h3>${runs || '<p class="muted">None.</p>'}`;
}

// ------------------------------------------------------------------- filters

function initFilters() {
  const domain = document.getElementById("filter-domain");
  for (const d of state.manifest.domains) domain.add(new Option(d.title, d.domain_id));
  const status = document.getElementById("filter-status");
  for (const s of state.manifest.statuses) status.add(new Option(s.status, s.status));

  const ids = ["filter-domain", "filter-status", "filter-kind"];
  const onChange = () => {
    state.filters = {
      domain: domain.value,
      status: status.value,
      kind: document.getElementById("filter-kind").value,
    };
    render();
  };
  for (const id of ids) document.getElementById(id).addEventListener("change", onChange);
  document.getElementById("filter-reset").addEventListener("click", () => {
    for (const id of ids) document.getElementById(id).value = "";
    onChange();
  });
}

function initLegend() {
  const items = [{ status: "not covered", rank: 0 }, ...state.manifest.statuses];
  document.getElementById("legend").innerHTML =
    items
      .map((s) => `<span><span class="swatch" style="background:var(--status-${s.rank})"></span>${escapeHtml(s.status)}</span>`)
      .join("") + `<span><span class="swatch" style="background:var(--marker);border-radius:50%"></span>station</span>`;
}

async function main() {
  try {
    state.manifest = await fetch("/api/manifest").then((r) => {
      if (!r.ok) throw new Error(`manifest: HTTP ${r.status}`);
      return r.json();
    });
  } catch (error) {
    panel().innerHTML = `<p class="gap">The explorer API did not answer: ${escapeHtml(error.message)}</p>`;
    return;
  }
  initFilters();
  initLegend();
  render();
  try {
    await initMap();
  } catch (error) {
    document.getElementById("map").innerHTML = `<p class="gap">Country boundaries could not be loaded: ${escapeHtml(error.message)}</p>`;
  }
}

main();
