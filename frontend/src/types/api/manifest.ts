/**
 * The API contract.
 *
 * These types are **derived** from the OpenAPI document the application
 * serves. The document is committed at `./openapi.json` and is written by the
 * application itself (`scripts/dump_openapi.py`); the TypeScript is generated
 * from it into `./generated.ts`. Nothing here is a copy of a schema: a type
 * here is a *name* for a schema there.
 *
 * That is the whole point. A hand-written mirror drifts — the first time a
 * field changed, the two would disagree and nothing would say so. Now a field
 * that changes in the API changes here too, and the drift is a failing gate
 * rather than a silent disagreement.
 *
 * The names keep the API's own `snake_case` words. There is deliberately
 * **one** contract: a camelCase mirror would be a second contract, free to
 * drift from the first, and a mapper is exactly the place where a `null` — an
 * unknown, which the API takes care to preserve — could quietly become a
 * zero.
 *
 * A field that is not known is `null`. It is never `0`, never `''`.
 */
import type { components } from '@/types/api/generated';

/**
 * A type that cannot be changed, and that is always there.
 *
 * The API's data is read, never written: the reader may not alter what the
 * repository says. The generated types are mutable, so they are frozen here.
 *
 * The `-?` is not a detail. A Pydantic field declared `Optional[str] = None`
 * is *not required* in the OpenAPI document — it has a default — yet the
 * response always carries it, with the value `null` when it is unknown. The
 * document is imprecise there; the responses are not. The type therefore says
 * what the API actually sends: the field is there, and it may be null.
 */
type Frozen<T> = T extends readonly (infer U)[]
  ? number extends T['length']
    ? readonly Frozen<U>[]
    : { readonly [K in keyof T]: Frozen<T[K]> }
  : T extends object
    ? { -readonly [K in keyof T]-?: Frozen<T[K]> }
    : T;

/** A schema of the OpenAPI document, frozen. */
type Schema<Name extends keyof components['schemas']> = Frozen<
  components['schemas'][Name]
>;

// ------------------------------------------------------------------- common

/** What a reference points at. */
export type RefKind = Schema<'Ref'>['kind'];

/**
 * A reference to the evidence behind a fact.
 *
 * A reference that resolves to a repository file carries its URL; one that
 * resolves to an importable name does not.
 */
export type ApiRef = Schema<'Ref'>;

/** A statement and the evidence it rests on. Never empty. */
export type ApiFact = Schema<'Fact'>;

/** One step of the closed vocabulary of what a mission produced. */
export type ApiStatusEntry = Schema<'StatusEntry'>;

// ---------------------------------------------------------------- catalogue

export type ApiDomain = Schema<'Domain'>;

export type ApiCountryDomain = Schema<'CountryDomain'>;

export type ApiCountrySummary = Schema<'CountrySummary'>;

export type ApiRegion = Schema<'Region'>;

/** A country, with the region-wide coverage that surrounds it. */
export type ApiCountryDetail = Schema<'CountryDetail'>;

export type ApiCoverageSubjectKind = Schema<'CoverageEntry'>['subject_kind'];

export type ApiCoverageEntry = Schema<'CoverageEntry'>;

export type ApiSurfaceProduct = Schema<'SurfaceProduct'>;

export type ApiPlannedFeature = Schema<'PlannedFeature'>;

export type ApiMarketIntelligence = Schema<'MarketIntelligence'>;

// ------------------------------------------------------------------ mission

export type ApiMission = Schema<'Mission'>;

// -------------------------------------------------------------------- asset

export type ApiAssetKind = Schema<'Asset'>['kind'];

/**
 * An asset.
 *
 * The two geometry fields are pairs and quadruples: the document declares
 * them with `prefixItems` and a fixed length, and the generator keeps that
 * length, so a reader never has to check it.
 */
export type ApiAsset = Schema<'Asset'>;

// ------------------------------------------------------------------- source

export type ApiSource = Schema<'Source'>;

// -------------------------------------------------------------------- model

export type ApiModel = Schema<'Model'>;

// ------------------------------------------------------------------- result

export type ApiPersistedResult = Schema<'PersistedResult'>;

export type ApiRunNotPersisted = Schema<'RunNotPersisted'>;

export type ApiResults = Schema<'Results'>;

// ----------------------------------------------------------------- manifest

export type ApiManifest = Schema<'Manifest'>;

export type ApiHealth = Schema<'Health'>;

/**
 * The structured part of an error response.
 *
 * These two are written by hand, and this is why: the error envelope is
 * produced by the application's exception handlers, not by a declared
 * response model, so it is not a schema of the OpenAPI document. It is the
 * one part of the contract that the document does not carry.
 */
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
