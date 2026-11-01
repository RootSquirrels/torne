/**
 * The API's types, generated from the OpenAPI document.
 *
 * This file is written by `scripts/generate_types.py` from
 * `frontend/src/types/api/openapi.json`, which the application itself writes.
 * It must not be edited by hand: the test suite refuses a file that the
 * document no longer produces.
 *
 * The document's own descriptions are carried over, so the contract the
 * reader sees is the contract the API publishes.
 */

export interface components {
    schemas: {
        /**
         * A physical object, where it is, and what was measured there.
         */
        Asset: {
            /**
             * The asset's identifier, as the source names it.
             */
            asset_id: string;
            /**
             * The extent of the asset, as (west, south, east, north) in the source's own reference frame.
             */
            bbox?: [number, number, number, number] | null;
            /**
             * ISO 3166-1 alpha-2 code of the country the asset is in.
             */
            country?: string | null;
            /**
             * The observation modality the asset belongs to.
             */
            domain_id: string;
            /**
             * What was measured at the asset.
             */
            facts: components["schemas"]["Fact"][];
            /**
             * The kind of physical asset.
             */
            kind: "station" | "catchment" | "raster_coverage";
            /**
             * The evidence for where the asset is.
             */
            location_ref: components["schemas"]["Ref"];
            /**
             * The missions that touched the asset.
             */
            mission_ids: string[];
            /**
             * The name of the asset.
             */
            name: string;
            /**
             * The position of the asset, as (longitude, latitude) in the source's own reference frame.
             */
            point?: [number, number] | null;
            /**
             * The source the asset was read from.
             */
            source_id: string;
        };
        /**
         * A country, with the region-wide coverage that surrounds it.
         */
        CountryDetail: {
            /**
             * The physical assets of the country.
             */
            asset_ids: string[];
            /**
             * ISO 3166-1 alpha-2 code of the country.
             */
            country: string;
            /**
             * Whether any mission of this country reached a status. False for a country no mission touched.
             */
            covered: boolean;
            /**
             * Each domain's status in the country.
             */
            domains: components["schemas"]["CountryDomain"][];
            /**
             * The region-wide scopes, which are not national statuses.
             */
            regions: components["schemas"]["Region"][];
        };
        /**
         * One domain's status in one country, earned by that country's missions.
         */
        CountryDomain: {
            /**
             * The physical assets of this country in the domain.
             */
            asset_ids: string[];
            /**
             * The domain's identifier.
             */
            domain_id: string;
            /**
             * Every mission of this country in the domain.
             */
            mission_ids: string[];
            /**
             * The models and methods those missions ran.
             */
            model_keys: string[];
            /**
             * The sources those missions read.
             */
            source_ids: string[];
            /**
             * The highest status this country's missions reached in the domain. Null when no mission of this country touched it. Region-wide coverage never colours a country.
             */
            status?: string | null;
            /**
             * The missions that earned the status.
             */
            status_from: string[];
            /**
             * The rank of that status, from 1 upwards. Zero when there is none.
             */
            status_rank: number;
            /**
             * The domain's name.
             */
            title: string;
        };
        /**
         * What one country holds, domain by domain.
         */
        CountrySummary: {
            /**
             * The physical assets of the country.
             */
            asset_ids: string[];
            /**
             * ISO 3166-1 alpha-2 code of the country.
             */
            country: string;
            /**
             * Each domain's status in the country.
             */
            domains: components["schemas"]["CountryDomain"][];
        };
        /**
         * A period that observations or a product cover.
         */
        CoverageEntry: {
            /**
             * The country, for an asset. Null for a region-wide product.
             */
            country?: string | null;
            /**
             * The observation modality the subject belongs to.
             */
            domain_id: string;
            /**
             * The last day of the period. Null when the end is not established.
             */
            end?: string | null;
            /**
             * Whether the period is still open, that is, not finished.
             */
            open: boolean;
            /**
             * The evidence for the period.
             */
            refs: components["schemas"]["Ref"][];
            /**
             * The first day of the period, as an ISO date, a year, or an ISO instant. Null when the start is not established.
             */
            start?: string | null;
            /**
             * The asset or product collection the period belongs to.
             */
            subject_id: string;
            /**
             * Whether the period belongs to a physical asset or to a surface product.
             */
            subject_kind: "asset" | "surface_product";
            /**
             * The name of the subject.
             */
            title: string;
        };
        /**
         * A modality of observation of the physical world.
         */
        Domain: {
            /**
             * The domain's identifier.
             */
            domain_id: string;
            /**
             * The package that reads this modality into observations.
             */
            semantic_layer: string;
            /**
             * The domain's name.
             */
            title: string;
        };
        /**
         * A statement and the evidence it rests on.
         */
        Fact: {
            /**
             * The evidence. Never empty: a fact without a reference cannot be built.
             */
            refs: components["schemas"]["Ref"][];
            /**
             * The statement, as the repository records it.
             */
            text: string;
        };
        /**
         * HTTPValidationError
         */
        HTTPValidationError: {
            /**
             * Detail
             */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * Whether the application is up, and which version it serves.
         */
        Health: {
            /**
             * The version of the manifest's shape.
             */
            manifest_version: string;
            /**
             * `ok` when the application can answer.
             */
            status: string;
            /**
             * The version of the TORNE package.
             */
            torne_version: string;
        };
        /**
         * The whole manifest: one JSON projection of what TORNE can show.
         * 
         * It is derived from the catalogue, from the surface-product registry and
         * from the code itself. Building it computes nothing scientific and calls no
         * provider.
         */
        Manifest: {
            /**
             * The physical assets the missions touched.
             */
            assets: components["schemas"]["Asset"][];
            /**
             * What each country holds.
             */
            countries: components["schemas"]["CountrySummary"][];
            /**
             * The periods observations and products cover.
             */
            coverage: components["schemas"]["CoverageEntry"][];
            /**
             * The observation modalities.
             */
            domains: components["schemas"]["Domain"][];
            /**
             * The version of the manifest's shape.
             */
            manifest_version: string;
            /**
             * The state of the market branch.
             */
            market_intelligence: components["schemas"]["MarketIntelligence"];
            /**
             * The missions and what they established.
             */
            missions: components["schemas"]["Mission"][];
            /**
             * The models and methods, and where they ran.
             */
            models: components["schemas"]["Model"][];
            /**
             * What is planned and not available.
             */
            planned: components["schemas"]["PlannedFeature"][];
            /**
             * The region-wide scopes.
             */
            regions: components["schemas"]["Region"][];
            /**
             * The repository the references link to.
             */
            repository_url: string;
            /**
             * What is published, and what was only run.
             */
            results: components["schemas"]["Results"];
            /**
             * The sources, and their established behaviour.
             */
            sources: components["schemas"]["Source"][];
            /**
             * The closed vocabulary of what a mission produced.
             */
            statuses: components["schemas"]["StatusEntry"][];
            /**
             * The surface observation products.
             */
            surface_products: components["schemas"]["SurfaceProduct"][];
            /**
             * The version of the TORNE package.
             */
            torne_version: string;
        };
        /**
         * The state of the market branch of the platform.
         */
        MarketIntelligence: {
            /**
             * Whether the market branch is open. It is not, today.
             */
            open: boolean;
            /**
             * Why it is closed, or why it is open.
             */
            reason: string;
        };
        /**
         * A mission, the status it reached, and what supports that status.
         */
        Mission: {
            /**
             * The physical assets the mission touched.
             */
            asset_ids: string[];
            /**
             * ISO 3166-1 alpha-2 codes of the countries the mission concerned. Empty for a region-wide mission.
             */
            countries: string[];
            /**
             * The observation modalities the mission touched.
             */
            domain_ids: string[];
            /**
             * The persisted knowledge records. Empty today: no record format exists on disk yet.
             */
            knowledge_records: components["schemas"]["Ref"][];
            /**
             * The mission's identifier, stable across versions.
             */
            mission_id: string;
            /**
             * The models and methods the mission ran.
             */
            model_keys: string[];
            /**
             * What the mission explicitly did not establish.
             */
            not_established: components["schemas"]["Fact"][];
            /**
             * What the mission established.
             */
            produced: components["schemas"]["Fact"][];
            /**
             * The scientific question the mission addressed.
             */
            question: string;
            /**
             * The region-wide scope, when the mission was not national.
             */
            region?: string | null;
            /**
             * The sources the mission read.
             */
            source_ids: string[];
            /**
             * What the mission produced: qualification, exploration, demonstration or knowledge. A knowledge status requires a persisted record.
             */
            status: string;
            /**
             * The evidence supporting the status. Never empty: a status without evidence cannot be built.
             */
            status_basis: components["schemas"]["Ref"][];
            /**
             * The rank of the status in the closed vocabulary, from 1 upwards. Ordered, comparable.
             */
            status_rank: number;
            /**
             * A one-line statement of what the mission did.
             */
            title: string;
        };
        /**
         * A model or method implemented in the repository, and where it ran.
         */
        Model: {
            /**
             * The observation modalities the model applies to.
             */
            domain_ids: string[];
            /**
             * Whether the model was executed on real data, as recorded by evidence.
             */
            executed_on_real_data: boolean;
            /**
             * The identity of the implementation, read from the code.
             */
            identity: string;
            /**
             * The importable name of the implementation.
             */
            identity_ref: components["schemas"]["Ref"];
            /**
             * The model's stable key.
             */
            key: string;
            /**
             * Whether the model produces a result (model) or tests a series (diagnostic).
             */
            kind: string;
            /**
             * The missions that ran the model.
             */
            mission_ids: string[];
            /**
             * The recorded runs, with their evidence.
             */
            runs: components["schemas"]["Fact"][];
            /**
             * What the model does.
             */
            title: string;
            /**
             * The version of the implementation, when the module exposes one.
             */
            version?: string | null;
            /**
             * The importable name holding the version, when there is one.
             */
            version_ref?: components["schemas"]["Ref"] | null;
        };
        /**
         * A knowledge product backed by a persisted record.
         */
        PersistedResult: {
            /**
             * The mission that produced the product.
             */
            mission_id: string;
            /**
             * The persisted records themselves.
             */
            records: components["schemas"]["Ref"][];
        };
        /**
         * A feature that is planned, and what it would need.
         */
        PlannedFeature: {
            /**
             * The planned feature.
             */
            feature: string;
            /**
             * What the feature would need before it could exist.
             */
            needs: string;
        };
        /**
         * A reference to the evidence behind a fact.
         * 
         * Every fact, status and coverage period carries references. A reference
         * that resolves to a repository file carries its URL; one that resolves to
         * an importable name does not.
         */
        Ref: {
            /**
             * What the reference points at.
             */
            kind: "mission" | "document" | "script" | "implementation" | "record";
            /**
             * The reference itself: a mission identifier, a repository path optionally followed by ' §section', or a 'module:attribute' name.
             */
            target: string;
            /**
             * Link to the referenced repository file, when the reference points at one.
             */
            url?: string | null;
        };
        /**
         * A region-wide scope, and the missions that covered it.
         */
        Region: {
            /**
             * The domains the region-wide missions touched.
             */
            domain_ids: string[];
            /**
             * The region's missions.
             */
            mission_ids: string[];
            /**
             * The region's name.
             */
            region: string;
            /**
             * The highest status the region's missions reached.
             */
            status: string;
        };
        /**
         * What the repository has published, and what it has only run.
         */
        Results: {
            /**
             * Why the published list is empty, when it is. Null once a record is persisted.
             */
            gap?: string | null;
            /**
             * The published knowledge products. Empty today: no record is persisted.
             */
            persisted: components["schemas"]["PersistedResult"][];
            /**
             * The runs that produced a product in memory, and were never persisted.
             */
            runs_not_persisted: components["schemas"]["RunNotPersisted"][];
        };
        /**
         * A run that produced a product in memory only.
         */
        RunNotPersisted: {
            /**
             * The mission that ran.
             */
            mission_id: string;
            /**
             * What the run produced.
             */
            produced: components["schemas"]["Fact"][];
            /**
             * The status the mission reached.
             */
            status: string;
        };
        /**
         * A source, the adapter that reads it, and its established behaviour.
         */
        Source: {
            /**
             * The adapter class that reads the source.
             */
            adapter: string;
            /**
             * The importable name of the adapter.
             */
            adapter_ref: components["schemas"]["Ref"];
            /**
             * The observation modality the source feeds.
             */
            domain_id: string;
            /**
             * The behaviour of the source, as established.
             */
            facts: components["schemas"]["Fact"][];
            /**
             * The missions that read the source.
             */
            mission_ids: string[];
            /**
             * The publication class of the source: p, b, c or n. Null when it is not established.
             */
            publication_class?: string | null;
            /**
             * Where the source is qualified.
             */
            qualified_in: components["schemas"]["Ref"];
            /**
             * The source's identifier, as the adapter declares it.
             */
            source_id: string;
            /**
             * The name of the source.
             */
            title: string;
        };
        /**
         * One step of the closed, ordered vocabulary of what a mission produced.
         */
        StatusEntry: {
            /**
             * The rank of the status in the vocabulary, from 1 upwards.
             */
            rank: number;
            /**
             * The status name, lower case.
             */
            status: string;
        };
        /**
         * A surface observation product, as the registry declares it.
         */
        SurfaceProduct: {
            /**
             * The collection identifier.
             */
            collection: string;
            /**
             * The last day covered, as an ISO instant.
             */
            coverage_end?: string | null;
            /**
             * The first day covered, as an ISO instant.
             */
            coverage_start?: string | null;
            /**
             * The declared meteorological dependence of the product.
             */
            dependence: string;
            /**
             * The instruments the product is built on.
             */
            instruments: string[];
            /**
             * The nature of the observation.
             */
            nature: string;
            /**
             * Whether the coverage is still open.
             */
            open_coverage: boolean;
            /**
             * The declared publication delay. Null when it is not established.
             */
            publication_delay?: string | null;
            /**
             * The quantity the product carries.
             */
            quantity: string;
            /**
             * The evidence for the registry entry.
             */
            refs: components["schemas"]["Ref"][];
            /**
             * The spatial resolution in metres. Null when it is not established.
             */
            resolution_m?: number | null;
            /**
             * The product's name.
             */
            title: string;
            /**
             * The unit of the quantity. Null when it is not established.
             */
            unit?: string | null;
            /**
             * Whether the unit is established, as opposed to declared by the producer only.
             */
            unit_established: boolean;
        };
        /**
         * ValidationError
         */
        ValidationError: {
            /**
             * Context
             */
            ctx?: Record<string, unknown>;
            /**
             * Input
             */
            input?: unknown;
            /**
             * Location
             */
            loc: (string | number)[];
            /**
             * Message
             */
            msg: string;
            /**
             * Error Type
             */
            type: string;
        };
    };
}
