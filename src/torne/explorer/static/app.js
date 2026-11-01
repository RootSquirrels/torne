// TORNE Explorer — map front end. It reads /api/manifest and nothing else:
// no computation, no call to a data provider.

const WORLD_TOPOJSON = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json";
const EUROPE_BOUNDS = [[34, -25], [72, 45]];

// ISO 3166-1 alpha-2 -> numeric, as used by world-atlas feature ids.
const ISO_NUMERIC = {
  AL: "008", AT: "040", BE: "056", BA: "070", BG: "100", BY: "112", CH: "756", CY: "196",
  CZ: "203", DE: "276", DK: "208", EE: "233", ES: "724", FI: "246", FR: "250", GB: "826",
  GR: "300", HR: "191", HU: "348", IE: "372", IS: "352", IT: "380", LT: "440", LU: "442",
  LV: "428", MD: "498", ME: "499", MK: "807", MT: "470", NL: "528", NO: "578", PL: "616",
  PT: "620", RO: "642", RS: "688", SE: "752", SI: "705", SK: "703", UA: "804", US: "840",
};
const NUMERIC_ISO = Object.fromEntries(Object.entries(ISO_NUMERIC).map(([a, n]) => [n, a]));

const state = { manifest: null, filters: { domain: "", status: "", kind: "" }, country: null };
let map;
let countryLayer;
let assetLayer;

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const statusRank = (label) => state.manifest.statuses.find((s) => s.status === label)?.rank ?? 0;

const badge = (label) => {
  const rank = label ? statusRank(label) : 0;
  return `<span class="badge s${rank}">${escapeHtml(label ?? "not covered")}</span>`;
};

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
  const missions = state.manifest.missions.filter((m) => m.asset_ids.includes(asset.asset_id));
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
        .on("click", () => showAsset(asset.asset_id))
        .addTo(assetLayer);
    } else if (asset.bbox) {
      const [w, s, e, n] = asset.bbox;
      L.rectangle([[s, w], [n, e]], { color: cssVar("--marker"), weight: 1, fill: false })
        .bindTooltip(escapeHtml(asset.name))
        .on("click", () => showAsset(asset.asset_id))
        .addTo(assetLayer);
    }
  }
}

function refreshMap() {
  if (!map) return;
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

async function initMap() {
  map = L.map("map", { zoomSnap: 0.25, worldCopyJump: true, attributionControl: true });
  map.fitBounds(EUROPE_BOUNDS);
  map.attributionControl.setPrefix(false).addAttribution("Boundaries: Natural Earth via world-atlas");
  assetLayer = L.layerGroup();

  const world = await fetch(WORLD_TOPOJSON).then((r) => r.json());
  const countries = topojson.feature(world, world.objects.countries);
  for (const feature of countries.features) unwrapAntimeridian(feature.geometry);
  countryLayer = L.geoJSON(countries, {
    style: styleCountry,
    onEachFeature: (feature, layer) => {
      const name = feature.properties?.name ?? "";
      layer.bindTooltip(escapeHtml(name), { sticky: true });
      layer.on("click", () => {
        const code = NUMERIC_ISO[feature.id];
        if (code) showCountry(code, name);
        else showUncovered(name);
      });
    },
  }).addTo(map);
  assetLayer.addTo(map);
  drawAssets();
  // The first fit can run before the grid layout settles; refit once it has,
  // and keep the size right when the window changes.
  map.invalidateSize();
  map.fitBounds(EUROPE_BOUNDS);
  new ResizeObserver(() => map.invalidateSize()).observe(document.getElementById("map"));
}

// --------------------------------------------------------------------- panel

const panel = () => document.getElementById("panel");
const backButton = () => `<button class="back" type="button" data-action="overview">← Europe overview</button>`;

function bindPanelActions() {
  panel().querySelectorAll("[data-action]").forEach((el) => {
    el.addEventListener("click", () => {
      const { action, id } = el.dataset;
      if (action === "overview") showOverview();
      if (action === "mission") showMission(id);
      if (action === "asset") showAsset(id);
    });
  });
}

function knowledgeSection() {
  const k = state.manifest.knowledge_products;
  if (k.items.length) {
    return k.items.map((item) => `<div class="card">${escapeHtml(item.title)}</div>`).join("");
  }
  return `<p class="gap">${escapeHtml(k.gap)}</p>`;
}

function missionCard(mission) {
  return `<div class="card">
    <div class="domain-row">
      <span class="card-title">${escapeHtml(mission.mission_id)}</span>${badge(mission.status)}
    </div>
    <p>${escapeHtml(mission.title)}</p>
    <button class="back" type="button" data-action="mission" data-id="${escapeHtml(mission.mission_id)}">Details →</button>
  </div>`;
}

function showOverview() {
  state.country = null;
  refreshMap();
  const regions = state.manifest.regions
    .map(
      (r) => `<div class="card"><div class="domain-row"><span class="card-title">${escapeHtml(r.region)}-wide</span>${badge(r.status)}</div>
      <p class="muted">${escapeHtml(r.domain_ids.join(", "))} · ${escapeHtml(r.mission_ids.join(", "))}</p></div>`,
    )
    .join("");
  const covered = state.manifest.countries
    .map((c) => {
      const best = Math.max(...c.domains.map((d) => d.status_rank));
      const label = state.manifest.statuses.find((s) => s.rank === best)?.status;
      return `<div class="card domain-row"><span>${escapeHtml(c.country)}</span>${badge(label)}</div>`;
    })
    .join("");
  panel().innerHTML = `
    <h2>Europe</h2>
    <p class="muted">Select a country. Colours show the highest status a country's missions have reached — earned by evidence, not declared.</p>
    <h3>Countries with missions</h3>${covered}
    <h3>Region-wide coverage</h3>${regions}
    <h3>Knowledge products</h3>${knowledgeSection()}
    <h3>Next mission</h3>
    <p>BASIN-001 — integrated catchment intelligence: one French catchment, three modalities, a first reconstruction of its water state.</p>`;
  bindPanelActions();
}

function showUncovered(name) {
  state.country = null;
  refreshMap();
  panel().innerHTML = `${backButton()}<h2>${escapeHtml(name)}</h2>
    <p class="muted">No mission has touched this country. Region-wide surface products may still cover it.</p>`;
  bindPanelActions();
}

function showCountry(code, name) {
  state.country = code;
  refreshMap();
  const summary = state.manifest.countries.find((c) => c.country === code);
  const missions = state.manifest.missions.filter((m) => m.countries.includes(code) && missionMatches(m));
  const regional = state.manifest.missions.filter((m) => m.region === "europe" && missionMatches(m));
  const assets = state.manifest.assets.filter((a) => a.country === code && assetMatches(a));
  const domains = (summary?.domains ?? state.manifest.domains.map((d) => ({ ...d, status: null })))
    .filter((d) => !state.filters.domain || d.domain_id === state.filters.domain)
    .map((d) => `<div class="card domain-row"><span>${escapeHtml(d.title)}</span>${badge(d.status)}</div>`)
    .join("");
  panel().innerHTML = `${backButton()}
    <h2>${escapeHtml(name || code)}</h2>
    <h3>Domains</h3>${domains}
    <h3>Missions</h3>${missions.map(missionCard).join("") || '<p class="muted">None matches the filters.</p>'}
    ${regional.length ? `<h3>Europe-wide</h3>${regional.map(missionCard).join("")}` : ""}
    <h3>Physical assets</h3>${
      assets
        .map(
          (a) => `<div class="card"><span class="card-title">${escapeHtml(a.name)}</span>
          <span class="muted"> · ${escapeHtml(a.kind)}</span>
          <button class="back" type="button" data-action="asset" data-id="${escapeHtml(a.asset_id)}">Details →</button></div>`,
        )
        .join("") || '<p class="muted">No asset matches the filters.</p>'
    }
    <h3>Knowledge products</h3>${knowledgeSection()}`;
  bindPanelActions();
}

function showMission(id) {
  const m = state.manifest.missions.find((x) => x.mission_id === id);
  if (!m) return;
  const sources = state.manifest.sources.filter((s) => m.source_ids.includes(s.source_id));
  panel().innerHTML = `${backButton()}
    <h2>${escapeHtml(m.mission_id)}</h2>${badge(m.status)}
    <p>${escapeHtml(m.title)}</p>
    <div class="card"><dl>
      <dt>Question</dt><dd>${escapeHtml(m.question)}</dd>
      <dt>Produced</dt><dd>${escapeHtml(m.produced)}</dd>
      <dt>Not established</dt><dd>${escapeHtml(m.not_established)}</dd>
      <dt>Records</dt><dd>${m.records.map(escapeHtml).join("<br>")}</dd>
    </dl></div>
    <h3>Sources</h3>${sources
      .map(
        (s) => `<div class="card"><span class="card-title">${escapeHtml(s.title)}</span><dl>
        <dt>Publication class</dt><dd>${escapeHtml(s.publication_class?.toUpperCase() ?? "not established")}</dd>
        <dt>Access</dt><dd>${escapeHtml(s.access)}</dd>
        <dt>Limit</dt><dd>${escapeHtml(s.limit)}</dd></dl></div>`,
      )
      .join("")}
    ${m.domain_ids.includes("earth_observation") ? surfaceProductsSection() : ""}`;
  bindPanelActions();
}

function surfaceProductsSection() {
  const rows = state.manifest.surface_products
    .map(
      (p) => `<div class="card"><span class="card-title">${escapeHtml(p.title)}</span><dl>
      <dt>Coverage</dt><dd>${escapeHtml((p.coverage_start ?? "?").slice(0, 10))} → ${escapeHtml(p.open_coverage ? "open" : (p.coverage_end ?? "?").slice(0, 10))}</dd>
      <dt>Dependence</dt><dd>${escapeHtml(p.dependence.replace("_", " "))}</dd>
      <dt>Nature</dt><dd>${escapeHtml(p.nature)}</dd></dl></div>`,
    )
    .join("");
  return `<h3>Surface products (${state.manifest.surface_products.length})</h3>${rows}`;
}

function showAsset(id) {
  const a = state.manifest.assets.find((x) => x.asset_id === id);
  if (!a) return;
  const source = state.manifest.sources.find((s) => s.source_id === a.source_id);
  const missions = state.manifest.missions.filter((m) => m.asset_ids.includes(a.asset_id));
  if (a.point) map.setView([a.point[1], a.point[0]], Math.max(map.getZoom(), 6));
  panel().innerHTML = `${backButton()}
    <h2>${escapeHtml(a.name)}</h2>
    <p class="muted">${escapeHtml(a.kind)} · ${escapeHtml(a.asset_id)}</p>
    <div class="card"><dl>
      <dt>Domain</dt><dd>${escapeHtml(a.domain_id)}</dd>
      <dt>Source</dt><dd>${escapeHtml(source?.title ?? a.source_id)}</dd>
      <dt>Period</dt><dd>${escapeHtml(a.period ? a.period.join(" → ") : "not measured")}</dd>
      <dt>Location</dt><dd>${escapeHtml(a.point ? `${a.point[1].toFixed(4)}, ${a.point[0].toFixed(4)}` : "—")}</dd>
    </dl></div>
    <h3>What was measured</h3>${a.facts.map((f) => `<p>${escapeHtml(f)}</p>`).join("") || '<p class="muted">Nothing recorded.</p>'}
    <h3>Missions</h3>${missions.map(missionCard).join("")}
    <h3>Models and knowledge products</h3>${knowledgeSection()}`;
  bindPanelActions();
}

// ------------------------------------------------------------------- filters

function initFilters() {
  const domain = document.getElementById("filter-domain");
  for (const d of state.manifest.domains) domain.add(new Option(d.title, d.domain_id));
  const status = document.getElementById("filter-status");
  for (const s of state.manifest.statuses) status.add(new Option(s.status, s.status));

  const onChange = () => {
    state.filters = {
      domain: domain.value,
      status: status.value,
      kind: document.getElementById("filter-kind").value,
    };
    refreshMap();
    if (state.country) {
      const name = countryLayer
        ?.getLayers()
        .find((l) => NUMERIC_ISO[l.feature.id] === state.country)?.feature.properties.name;
      showCountry(state.country, name);
    }
  };
  for (const id of ["filter-domain", "filter-status", "filter-kind"]) {
    document.getElementById(id).addEventListener("change", onChange);
  }
  document.getElementById("filter-reset").addEventListener("click", () => {
    for (const id of ["filter-domain", "filter-status", "filter-kind"]) document.getElementById(id).value = "";
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
  showOverview();
  try {
    await initMap();
  } catch (error) {
    document.getElementById("map").innerHTML = `<p class="gap">Country boundaries could not be loaded: ${escapeHtml(error.message)}</p>`;
  }
}

main();
