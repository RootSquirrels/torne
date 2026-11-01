/**
 * The explorer.
 *
 * The map on the left, the reading panel on the right, the filters above.
 *
 * Everything that matters is in the URL: what is being read, and which
 * filters narrow it. A reader can therefore share a link to exactly what
 * they are looking at.
 */
import { useCallback, useMemo } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { ErrorState } from '@/components/ui/ErrorState';
import { FilterBar } from '@/components/ui/FilterBar';
import { LoadingState } from '@/components/ui/LoadingState';
import { Select } from '@/components/ui/Select';
import { WorldMap } from '@/features/explorer/WorldMap';
import { ISO_NUMERIC_TO_ALPHA } from '@/features/explorer/countryCodes';
import { EMPTY_FILTERS } from '@/features/explorer/filters';
import type { ExplorerFilters } from '@/features/explorer/filters';
import { useBoundaries } from '@/features/explorer/useBoundaries';
import { useManifest } from '@/features/explorer/useManifest';
import {
  Asset,
  Coverage,
  Country,
  Domain,
  Mission,
  Models,
  Overview,
  Results,
  Source,
  statusLegend,
  Uncovered,
} from '@/features/explorer/views';
import type { ExplorerContext } from '@/features/explorer/views';
import './ExplorerRoute.css';

export function ExplorerRoute() {
  const state = useManifest();
  const boundaries = useBoundaries();
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();
  const [search, setSearch] = useSearchParams();

  const filters = useMemo<ExplorerFilters>(
    () => ({
      domain: search.get('domain') ?? '',
      status: search.get('status') ?? '',
      kind: search.get('kind') ?? '',
    }),
    [search],
  );

  const setFilter = useCallback(
    (name: keyof ExplorerFilters, value: string) => {
      const next = new URLSearchParams(search);
      if (value === '') {
        next.delete(name);
      } else {
        next.set(name, value);
      }
      void setSearch(next, { replace: true });
    },
    [search, setSearch],
  );

  const go = useCallback(
    (path: string) => {
      void navigate(path);
    },
    [navigate],
  );

  const countryName = useCallback(
    (code: string) => {
      const found = boundaries.features.find((feature) => {
        const alpha = ISO_NUMERIC_TO_ALPHA[String(feature.id ?? '')];
        return alpha === code;
      });
      return found?.properties?.name ?? code;
    },
    [boundaries.features],
  );

  if (state.status === 'loading') {
    return (
      <div className="torne-explorer__loading">
        <LoadingState label="Loading the manifest…" />
      </div>
    );
  }

  if (state.status === 'failed') {
    return (
      <div className="torne-explorer__loading">
        <ErrorState
          title="The explorer API did not answer"
          message={state.message}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  const { manifest } = state;
  const context: ExplorerContext = {
    manifest,
    filters,
    navigate: go,
    countryName,
    domainTitle: (id: string) =>
      manifest.domains.find((domain) => domain.domain_id === id)?.title ?? id,
  };

  const view = (() => {
    if (params.code !== undefined && params.domainId !== undefined) {
      return <Domain context={context} code={params.code} domainId={params.domainId} />;
    }
    if (params.code !== undefined) {
      return <Country context={context} code={params.code} />;
    }
    if (params.missionId !== undefined) {
      return <Mission context={context} missionId={params.missionId} />;
    }
    if (params.assetId !== undefined) {
      return <Asset context={context} assetId={params.assetId} />;
    }
    if (params.sourceId !== undefined) {
      return <Source context={context} sourceId={params.sourceId} />;
    }
    if (params.key !== undefined) {
      return <Models context={context} key={params.key} />;
    }
    if (location.pathname === '/models') {
      return <Models context={context} />;
    }
    if (location.pathname === '/coverage') {
      return <Coverage context={context} />;
    }
    if (location.pathname === '/results') {
      return <Results context={context} />;
    }
    return <Overview context={context} />;
  })();

  const selectedId = params.assetId ?? params.code ?? null;

  return (
    <div className="torne-explorer">
      <FilterBar
        onReset={() => void setSearch(new URLSearchParams(), { replace: true })}
        resetLabel="Reset filters"
      >
        <Select
          label="Domain"
          value={filters.domain}
          onChange={(value) => setFilter('domain', value)}
          options={[
            { value: '', label: 'All domains' },
            ...manifest.domains.map((domain) => ({
              value: domain.domain_id,
              label: domain.title,
            })),
          ]}
        />
        <Select
          label="Minimum status"
          value={filters.status}
          onChange={(value) => setFilter('status', value)}
          options={[
            { value: '', label: 'Any status' },
            ...manifest.statuses.map((entry) => ({
              value: entry.status,
              label: entry.status,
            })),
          ]}
        />
        <Select
          label="Asset kind"
          value={filters.kind}
          onChange={(value) => setFilter('kind', value)}
          options={[
            { value: '', label: 'All kinds' },
            { value: 'station', label: 'Stations' },
            { value: 'catchment', label: 'Catchments' },
            { value: 'raster_coverage', label: 'Raster coverages' },
          ]}
        />
        {/*
          There is no period filter and no uncertainty filter, and there will
          not be one until a knowledge record exists to filter on: the API
          carries no period and no uncertainty. The overview says so in the
          reader's own words, under "Planned, not available", and the manifest
          drives that list. A dropdown that cannot filter is a promise kept in
          the wrong place.
        */}
      </FilterBar>

      <div className="torne-explorer__body">
        <div className="torne-explorer__map">
          <WorldMap
            manifest={manifest}
            filters={filters}
            features={boundaries.features}
            selectedId={selectedId}
            onSelectCountry={(code) => go(`/country/${code}`)}
            onSelectAsset={(assetId) => go(`/asset/${assetId}`)}
            legend={statusLegend(manifest)}
          />
          {boundaries.failure !== null ? (
            <p className="torne-explorer__gap" role="status">
              Country boundaries could not be loaded: {boundaries.failure}
            </p>
          ) : null}
        </div>

        <aside className="torne-explorer__panel" aria-label="Reading panel">
          {view}
        </aside>
      </div>
    </div>
  );
}

export { EMPTY_FILTERS, Uncovered };
