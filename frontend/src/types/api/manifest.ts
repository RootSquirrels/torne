/**
 * The API contract.
 *
 * These types mirror the Pydantic schemas the explorer serves, field for
 * field, and they keep the API's own `snake_case` names. There is deliberately
 * **one** definition: a camelCase mirror would be a second contract, free to
 * drift from the first, and a mapper is exactly the place where a `null` — an
 * unknown, which the API takes care to preserve — could quietly become a
 * zero.
 *
 * A field that is not known is `null`. It is never `0`, never `''`.
 */

// ------------------------------------------------------------------- common

/** What a reference points at. */
export type RefKind = 'mission' | 'document' | 'script' | 'implementation' | 'record';

/**
 * A reference to the evidence behind a fact.
 *
 * A reference that resolves to a repository file carries its URL; one that
 * resolves to an importable name does not.
 */
export interface ApiRef {
  readonly kind: RefKind;
  readonly target: string;
  readonly url: string | null;
}

/** A statement and the evidence it rests on. Never empty. */
export interface ApiFact {
  readonly text: string;
  readonly refs: readonly ApiRef[];
}

/** One step of the closed vocabulary of what a mission produced. */
export interface ApiStatusEntry {
  readonly status: string;
  readonly rank: number;
}

// ---------------------------------------------------------------- catalogue

export interface ApiDomain {
  readonly domain_id: string;
  readonly title: string;
  readonly semantic_layer: string;
}

export interface ApiCountryDomain {
  readonly domain_id: string;
  readonly title: string;
  readonly status: string | null;
  readonly status_rank: number;
  readonly status_from: readonly string[];
  readonly mission_ids: readonly string[];
  readonly source_ids: readonly string[];
  readonly model_keys: readonly string[];
  readonly asset_ids: readonly string[];
}

export interface ApiCountrySummary {
  readonly country: string;
  readonly domains: readonly ApiCountryDomain[];
  readonly asset_ids: readonly string[];
}

export interface ApiRegion {
  readonly region: string;
  readonly domain_ids: readonly string[];
  readonly status: string;
  readonly mission_ids: readonly string[];
}

/** A country, with the region-wide coverage that surrounds it. */
export interface ApiCountryDetail extends ApiCountrySummary {
  readonly covered: boolean;
  readonly regions: readonly ApiRegion[];
}

export type ApiCoverageSubjectKind = 'asset' | 'surface_product';

export interface ApiCoverageEntry {
  readonly subject_kind: ApiCoverageSubjectKind;
  readonly subject_id: string;
  readonly title: string;
  readonly domain_id: string;
  readonly country: string | null;
  readonly start: string | null;
  readonly end: string | null;
  readonly open: boolean;
  readonly refs: readonly ApiRef[];
}

export interface ApiSurfaceProduct {
  readonly collection: string;
  readonly title: string;
  readonly quantity: string;
  readonly nature: string;
  readonly resolution_m: number | null;
  readonly coverage_start: string | null;
  readonly coverage_end: string | null;
  readonly open_coverage: boolean;
  readonly dependence: string;
  readonly unit: string | null;
  readonly unit_established: boolean;
  readonly publication_delay: string | null;
  readonly instruments: readonly string[];
  readonly refs: readonly ApiRef[];
}

export interface ApiPlannedFeature {
  readonly feature: string;
  readonly needs: string;
}

export interface ApiMarketIntelligence {
  readonly open: boolean;
  readonly reason: string;
}

// ------------------------------------------------------------------ mission

export interface ApiMission {
  readonly mission_id: string;
  readonly title: string;
  readonly status: string;
  readonly status_rank: number;
  readonly status_basis: readonly ApiRef[];
  readonly domain_ids: readonly string[];
  readonly countries: readonly string[];
  readonly region: string | null;
  readonly question: string;
  readonly produced: readonly ApiFact[];
  readonly not_established: readonly ApiFact[];
  readonly asset_ids: readonly string[];
  readonly source_ids: readonly string[];
  readonly model_keys: readonly string[];
  readonly knowledge_records: readonly ApiRef[];
}

// -------------------------------------------------------------------- asset

export type ApiAssetKind = 'station' | 'catchment' | 'raster_coverage';

export interface ApiAsset {
  readonly asset_id: string;
  readonly kind: ApiAssetKind;
  readonly name: string;
  readonly country: string | null;
  readonly domain_id: string;
  readonly source_id: string;
  /** (longitude, latitude) in the source's own reference frame. */
  readonly point: readonly [number, number] | null;
  /** (west, south, east, north) in the source's own reference frame. */
  readonly bbox: readonly [number, number, number, number] | null;
  readonly location_ref: ApiRef;
  readonly facts: readonly ApiFact[];
  readonly mission_ids: readonly string[];
}

// ------------------------------------------------------------------- source

export interface ApiSource {
  readonly source_id: string;
  readonly title: string;
  readonly adapter: string;
  readonly adapter_ref: ApiRef;
  readonly domain_id: string;
  readonly publication_class: string | null;
  readonly qualified_in: ApiRef;
  readonly facts: readonly ApiFact[];
  readonly mission_ids: readonly string[];
}

// -------------------------------------------------------------------- model

export interface ApiModel {
  readonly key: string;
  readonly title: string;
  readonly kind: string;
  readonly domain_ids: readonly string[];
  readonly identity: string;
  readonly identity_ref: ApiRef;
  readonly version: string | null;
  readonly version_ref: ApiRef | null;
  readonly executed_on_real_data: boolean;
  readonly runs: readonly ApiFact[];
  readonly mission_ids: readonly string[];
}

// ------------------------------------------------------------------- result

export interface ApiPersistedResult {
  readonly mission_id: string;
  readonly records: readonly ApiRef[];
}

export interface ApiRunNotPersisted {
  readonly mission_id: string;
  readonly status: string;
  readonly produced: readonly ApiFact[];
}

export interface ApiResults {
  readonly persisted: readonly ApiPersistedResult[];
  readonly runs_not_persisted: readonly ApiRunNotPersisted[];
  readonly gap: string | null;
}

// ----------------------------------------------------------------- manifest

export interface ApiManifest {
  readonly manifest_version: string;
  readonly torne_version: string;
  readonly repository_url: string;
  readonly statuses: readonly ApiStatusEntry[];
  readonly domains: readonly ApiDomain[];
  readonly countries: readonly ApiCountrySummary[];
  readonly regions: readonly ApiRegion[];
  readonly missions: readonly ApiMission[];
  readonly assets: readonly ApiAsset[];
  readonly coverage: readonly ApiCoverageEntry[];
  readonly sources: readonly ApiSource[];
  readonly models: readonly ApiModel[];
  readonly surface_products: readonly ApiSurfaceProduct[];
  readonly results: ApiResults;
  readonly planned: readonly ApiPlannedFeature[];
  readonly market_intelligence: ApiMarketIntelligence;
}

export interface ApiHealth {
  readonly status: string;
  readonly torne_version: string;
  readonly manifest_version: string;
}

/** The structured part of an error response. */
export interface ApiErrorBody {
  readonly code: string;
  readonly message: string;
  readonly details: Record<string, unknown> | null;
}

/** Every error carries `detail` (the legacy shape) and `error` (the structured one). */
export interface ApiErrorResponse {
  readonly detail: string;
  readonly error: ApiErrorBody;
}
