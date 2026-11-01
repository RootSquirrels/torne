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
         * The control of a country's terminals against the aggregate it publishes.
         */
        AggregateSumControl: {
            /**
             * The country.
             */
            country: string;
            /**
             * The aggregate the platform publishes, in GWh.
             */
            published_aggregate_gwh: number;
            /**
             * The difference between the two, as a fraction.
             */
            relative_difference: number;
            /**
             * How many terminals were counted.
             */
            terminals_counted: number;
            /**
             * The sum of the terminals' reserves, in GWh.
             */
            terminals_sum_gwh: number;
        };
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
         * One branch of the platform, and whether it is open.
         * 
         * A branch is an application of what the repository has established. It is
         * open when the products it consumes are themselves validated, and closed
         * otherwise — and a closed branch says why, in words a reader can check.
         */
        Branch: {
            /**
             * The branch's identifier.
             */
            branch_id: string;
            /**
             * The observation modalities it reads.
             */
            domain_ids?: string[];
            /**
             * The missions behind it.
             */
            mission_ids?: string[];
            /**
             * Whether the branch is open.
             */
            open: boolean;
            /**
             * The published products it serves.
             */
            product_ids?: string[];
            /**
             * Why it is closed, or why it is open.
             */
            reason: string;
            /**
             * What the branch is called.
             */
            title: string;
        };
        /**
         * One day of one terminal, seen by two independent sources.
         */
        ConfrontationRow: {
            /**
             * The difference between the two, in GWh.
             */
            absolute_difference_gwh?: number | null;
            /**
             * The day the platform describes.
             */
            alsi_day: string;
            /**
             * The stock the platform publishes, in GWh.
             */
            alsi_stock_gwh?: number | null;
            /**
             * The day the operator describes.
             */
            operator_day: string;
            /**
             * The stock the operator publishes, in GWh.
             */
            operator_stock_gwh?: number | null;
            /**
             * The terminal, in the operator's words.
             */
            operator_terminal: string;
            /**
             * The difference between the two, as a fraction.
             */
            relative_difference?: number | null;
            /**
             * Its identifier.
             */
            terminal_eic: string;
        };
        /**
         * The confrontation, in full.
         */
        ConfrontationRows: {
            /**
             * How many comparisons it holds.
             */
            comparisons: number;
            /**
             * The product the confrontation validates.
             */
            product_id: string;
            /**
             * The comparisons themselves.
             */
            rows: components["schemas"]["ConfrontationRow"][];
        };
        /**
         * What one country holds, and what it lets out.
         */
        CountryDependency: {
            /**
             * Its capacity, in GWh.
             */
            capacity_gwh: number;
            /**
             * Its share of the European capacity.
             */
            capacity_share: number;
            /**
             * Its send-out, in GWh per day.
             */
            send_out_gwh_per_day: number;
            /**
             * Its share of the European send-out.
             */
            send_out_share: number;
            /**
             * Its reserve, in GWh.
             */
            stock_gwh: number;
            /**
             * Its share of the European reserve.
             */
            stock_share: number;
            /**
             * How many terminals it holds.
             */
            terminals: number;
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
         * What the loss of one installation costs the system.
         */
        LossScenario: {
            /**
             * The coverage after, in days.
             */
            coverage_after_days: number;
            /**
             * The coverage before, in days.
             */
            coverage_before_days: number;
            /**
             * The days of coverage it costs.
             */
            days_lost: number;
            /**
             * The send-out it carries, in GWh per day.
             */
            flow_lost_gwh_per_day: number;
            /**
             * The installation that is lost.
             */
            installation: string;
            /**
             * The reserve it carries, in GWh.
             */
            reserve_lost_gwh: number;
            /**
             * Its share of the European reserve.
             */
            reserve_share_lost: number;
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
             * The branches of the platform, and whether they are open.
             */
            branches: components["schemas"]["Branch"][];
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
         * A quantity that is a bound, and not a measurement.
         */
        ProductBound: {
            /**
             * `lower` or `upper`: which way the true value lies.
             */
            direction: string;
            /**
             * What the bound concerns.
             */
            quantity: string;
            /**
             * Why the quantity is a bound, in clear language.
             */
            statement: string;
        };
        /**
         * A published product, in full.
         */
        ProductDetail: {
            /**
             * The quantities that are bounds, not measurements.
             */
            bounds: components["schemas"]["ProductBound"][];
            /**
             * Where the product holds, and where it does not.
             */
            domain_of_validity: string;
            /**
             * When the published payload was generated.
             */
            generated_at?: string | null;
            /**
             * The indicators of each layer, typed by the layer they belong to.
             */
            indicators: components["schemas"]["ProductIndicators"];
            /**
             * The quality status of each entry it consumed.
             */
            input_statuses: Record<string, unknown>;
            /**
             * The layers it publishes, and the columns they carry.
             */
            layers: Record<string, unknown>;
            /**
             * Its lineage, from the sources to the evaluation.
             */
            lineage: components["schemas"]["ProductRef"][];
            /**
             * The nature of the result it publishes.
             */
            nature: string;
            /**
             * The digest of the payload it publishes.
             */
            payload_digest: string;
            /**
             * The files the payload is made of.
             */
            payload_files: string[];
            /**
             * When the product was established.
             */
            produced_at: string;
            /**
             * The stable identifier of the product.
             */
            product_id: string;
            /**
             * Where its numbers come from.
             */
            provenance: components["schemas"]["ProductProvenance"];
            /**
             * The entries it consumed whose status is provisional.
             */
            provisional_inputs?: string[];
            /**
             * The day the published states are the state of.
             */
            reference_date?: string | null;
            /**
             * Its status: usable, degraded, withdrawn or inconclusive.
             */
            status: string;
            /**
             * What the product is.
             */
            title: string;
            /**
             * Its uncertainty, qualified in clear language.
             */
            uncertainty: string;
            /**
             * The units its quantities are expressed in.
             */
            units: components["schemas"]["ProductUnits"];
            /**
             * The confrontation that validated it.
             */
            validation: components["schemas"]["ProductValidation"];
            /**
             * The version of the product.
             */
            version: string;
            /**
             * The period each layer covers.
             */
            windows: Record<string, unknown>;
        };
        /**
         * The indicators of each layer of the product.
         * 
         * They are typed, layer by layer, because a reader must be able to trust
         * what a number means without reading the production code that produced it.
         */
        ProductIndicators: {
            /**
             * What the underground storage layer publishes.
             */
            storage: components["schemas"]["StorageIndicators"];
            /**
             * What the LNG terminal layer publishes.
             */
            terminals: components["schemas"]["TerminalIndicators"];
        };
        /**
         * One physical layer of a product, and the columns it publishes.
         */
        ProductLayer: {
            /**
             * The column that carries its country.
             */
            country_column: string;
            /**
             * The column that carries the gas day.
             */
            day_column: string;
            /**
             * The column that names the entity the state belongs to.
             */
            entity_column: string;
            /**
             * The published file that carries it.
             */
            file: string;
            /**
             * The flags it publishes, by column.
             */
            flags?: Record<string, unknown>;
            /**
             * The layer's identifier.
             */
            id: string;
            /**
             * The column that names it for a reader.
             */
            label_column: string;
            /**
             * The quantities it publishes, by column.
             */
            measures?: Record<string, unknown>;
            /**
             * The columns that place it.
             */
            position_columns?: string[];
            /**
             * The column that carries the publication instant.
             */
            published_column: string;
            /**
             * What the layer is.
             */
            title: string;
        };
        /**
         * The products the repository has published.
         */
        ProductList: {
            /**
             * The published products.
             */
            products: components["schemas"]["ProductSummary"][];
        };
        /**
         * Where the product's numbers come from.
         */
        ProductProvenance: {
            /**
             * Where the identifiers of the entities come from.
             */
            identifier_reference?: string | null;
            /**
             * The digest of each production file the product was built from.
             */
            production_digests?: Record<string, unknown>;
            /**
             * The sources it consumed.
             */
            sources?: components["schemas"]["SourceDescription"][];
        };
        /**
         * A quantity the product publishes, with what it means and in what unit.
         */
        ProductQuantity: {
            /**
             * What the quantity is.
             */
            label: string;
            /**
             * The unit it is expressed in.
             */
            unit?: string | null;
        };
        /**
         * One link of a product's lineage.
         */
        ProductRef: {
            /**
             * The stable identifier of the object cited.
             */
            identifier: string;
            /**
             * What the reference points at: a source, an observation, an evaluation.
             */
            kind: string;
            /**
             * A human-readable name for it.
             */
            label?: string | null;
            /**
             * Its version, when it has one.
             */
            revision?: string | null;
        };
        /**
         * One state of one entity.
         */
        ProductState: {
            /**
             * Its country.
             */
            country: string;
            /**
             * The entity the state belongs to.
             */
            entity: string;
            /**
             * The flags of the state.
             */
            flags: Record<string, unknown>;
            /**
             * The day the state describes.
             */
            gas_day: string;
            /**
             * Its name for a reader.
             */
            label: string;
            /**
             * Its latitude, when it is placed.
             */
            latitude?: number | null;
            /**
             * Its longitude, when it is placed.
             */
            longitude?: number | null;
            /**
             * When the state was published.
             */
            published_at: string;
            /**
             * The quantities of the state. A quantity that is not known is null.
             */
            values: Record<string, unknown>;
        };
        /**
         * The states of one layer.
         */
        ProductStates: {
            /**
             * The layer they belong to.
             */
            layer: string;
            /**
             * The product the states belong to.
             */
            product_id: string;
            /**
             * The states themselves.
             */
            states: components["schemas"]["ProductState"][];
        };
        /**
         * A published product, as the list shows it.
         */
        ProductSummary: {
            /**
             * Where the product holds, and where it does not.
             */
            domain_of_validity: string;
            /**
             * The nature of the result it publishes.
             */
            nature: string;
            /**
             * The digest of the payload it publishes.
             */
            payload_digest: string;
            /**
             * When the product was established.
             */
            produced_at: string;
            /**
             * The stable identifier of the product.
             */
            product_id: string;
            /**
             * Its status: usable, degraded, withdrawn or inconclusive.
             */
            status: string;
            /**
             * What the product is.
             */
            title: string;
            /**
             * Its uncertainty, qualified in clear language.
             */
            uncertainty: string;
            /**
             * The version of the product. A correction is a new version.
             */
            version: string;
        };
        /**
         * The units the product's quantities are expressed in.
         * 
         * The measures are the units of the columns of the payload; the published
         * ones are the units each source states for itself.
         */
        ProductUnits: {
            /**
             * The unit of each measure, by layer and by column.
             */
            measures?: Record<string, unknown>;
            /**
             * The units each source publishes for itself, by layer.
             */
            published?: Record<string, unknown>;
        };
        /**
         * The confrontation that validated the product, and what it found.
         */
        ProductValidation: {
            /**
             * How the two sources' days were aligned.
             */
            aligned_days?: string | null;
            /**
             * How many comparisons were made.
             */
            comparisons: number;
            /**
             * The largest relative difference, as a fraction.
             */
            max_relative_difference?: number | null;
            /**
             * The median relative difference, as a fraction.
             */
            median_relative_difference?: number | null;
            /**
             * The median relative difference on the network flow.
             */
            median_relative_difference_network_flow?: number | null;
            /**
             * The median relative difference on the volumes.
             */
            median_relative_difference_volume?: number | null;
            /**
             * How the product was confronted with an independent source.
             */
            method: string;
            /**
             * What the residual difference turned out to be.
             */
            residual?: string | null;
        };
        /**
         * The period a layer covers.
         * 
         * The counts are optional: a layer that publishes its own window may count
         * its states and entities, and a window that only bounds the period says
         * so. A count that is not published stays null.
         */
        ProductWindow: {
            /**
             * The last day of the period.
             */
            end: string;
            /**
             * How many entities the period covers.
             */
            entities?: number | null;
            /**
             * The first day of the period.
             */
            start: string;
            /**
             * How many states the period holds.
             */
            states?: number | null;
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
         * One source the product consumed.
         */
        SourceDescription: {
            /**
             * How it is reached.
             */
            access: string;
            /**
             * Which dataset of theirs it is.
             */
            dataset: string;
            /**
             * Where the identifiers of the entities come from, when it is not this source.
             */
            identifier_reference?: string | null;
            /**
             * Who publishes it.
             */
            publisher: string;
            /**
             * The source's identifier.
             */
            source_id: string;
            /**
             * The units it publishes.
             */
            units: string;
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
         * How the reserve is concentrated among the countries.
         */
        StorageConcentration: {
            /**
             * The Herfindahl index of the national reserves.
             */
            herfindahl: number;
            /**
             * The share the first country carries.
             */
            top_country_share: number;
            /**
             * The share the three first carry.
             */
            top_three_countries_share: number;
        };
        /**
         * What one country's underground storage holds.
         */
        StorageCountryIndicator: {
            /**
             * Its capacity, in GWh.
             */
            capacity_gwh: number;
            /**
             * The computed coverage, in days. It is an upper bound.
             */
            computed_coverage_days: number;
            /**
             * The country.
             */
            country: string;
            /**
             * How many days of the period it covers.
             */
            days: number;
            /**
             * How fast it draws down, in days of coverage per day.
             */
            degradation_days_per_day: number;
            /**
             * The difference between the computed coverage and the published autonomy, in days.
             */
            difference_with_published_days: number;
            /**
             * When the state was published.
             */
            published_at: string;
            /**
             * The autonomy the platform publishes, in days.
             */
            published_autonomy_days: number;
            /**
             * The published autonomy divided by the published consumption, in days.
             */
            published_autonomy_on_consumption_days: number;
            /**
             * The ratio of the published autonomy to the published consumption.
             */
            published_autonomy_over_consumption_ratio: number;
            /**
             * The published fill, in per cent.
             */
            published_fill_pct: number;
            /**
             * How fast it refills, per day.
             */
            reconstitution_rate_per_day: number;
            /**
             * Its reserve, in GWh.
             */
            stock_gwh: number;
        };
        /**
         * What the storage layer publishes.
         */
        StorageIndicators: {
            /**
             * How the reserve is concentrated.
             */
            concentration: components["schemas"]["StorageConcentration"];
            /**
             * The countries it answered for that published no usable state. They are not missing data: they are declared absences.
             */
            countries_without_published_state?: string[];
            /**
             * The countries the platform answered for.
             */
            coverage?: string[];
            /**
             * What each country holds.
             */
            indicators?: components["schemas"]["StorageCountryIndicator"][];
            /**
             * The period it covers.
             */
            period: components["schemas"]["ProductWindow"];
            /**
             * Where its numbers come from.
             */
            provenance: components["schemas"]["StorageProvenance"];
            /**
             * The refusals it recorded.
             */
            refusals?: string[];
            /**
             * The units it publishes.
             */
            units: components["schemas"]["StorageUnits"];
        };
        /**
         * Where the storage layer's numbers come from.
         */
        StorageProvenance: {
            /**
             * How it is reached.
             */
            api: string;
            /**
             * The attribution it requires.
             */
            attribution: string;
            /**
             * How the key is carried.
             */
            credential: string;
            /**
             * The platform that publishes them.
             */
            source: string;
        };
        /**
         * The units the storage layer publishes.
         */
        StorageUnits: {
            /**
             * The unit of the flows.
             */
            flow: string;
            /**
             * The unit of the reserves.
             */
            stock: string;
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
         * How the reserve is concentrated among the installations.
         */
        TerminalConcentration: {
            /**
             * The Herfindahl index of the reserve among the installations.
             */
            herfindahl: number;
            /**
             * The share of the reserve the first installation carries.
             */
            top_share: number;
            /**
             * The share the three first carry.
             */
            top_three_share: number;
            /**
             * The European reserve, in GWh.
             */
            total_gwh: number;
        };
        /**
         * What the terminal layer publishes.
         */
        TerminalIndicators: {
            /**
             * The control of each country's terminals against its aggregate.
             */
            aggregate_sum_control?: components["schemas"]["AggregateSumControl"][];
            /**
             * How the reserve is concentrated.
             */
            concentration: components["schemas"]["TerminalConcentration"];
            /**
             * The Herfindahl index of the reserve among the countries.
             */
            concentration_by_country: number;
            /**
             * What each country holds and lets out.
             */
            dependency_by_country?: Record<string, unknown>;
            /**
             * When the indicators were computed.
             */
            generated_at: string;
            /**
             * How many installations the layer carries.
             */
            installations: number;
            /**
             * The installations the platform lists but publishes nothing for.
             */
            installations_without_data?: string[];
            /**
             * What the loss of each installation costs.
             */
            loss_scenarios?: components["schemas"]["LossScenario"][];
            /**
             * The product, in the words of the mission that produced it.
             */
            product: string;
            /**
             * The day they are the state of.
             */
            reference_date: string;
            /**
             * The sources they come from.
             */
            sources?: components["schemas"]["SourceDescription"][];
            /**
             * How many states the layer holds.
             */
            states: number;
            /**
             * The coverage of the system, in days. It is an upper bound.
             */
            system_coverage_days: number;
            /**
             * The send-out of the system, in GWh per day.
             */
            system_flow_gwh_per_day: number;
            /**
             * The exploitable reserve of the system, in GWh.
             */
            system_reserve_gwh: number;
            /**
             * The period they cover.
             */
            window: components["schemas"]["ProductWindow"];
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
