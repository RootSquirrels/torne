/**
 * The views of the explorer.
 *
 * Each view answers one question about the catalogue, and shows the evidence
 * behind every claim it makes. The rules that hold everywhere:
 *
 * - a status is always accompanied by the references that support it;
 * - a run that produced a product in memory is never presented as a
 *   published result;
 * - a country that no mission touched is shown as such, not hidden;
 * - a planned feature is listed as planned, never as a control that works.
 */
import { lazy, Suspense } from 'react';
import type { ReactNode } from 'react';

import { Breadcrumbs } from '@/components/ui/Breadcrumbs';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { Legend } from '@/components/ui/Legend';
import { LoadingState } from '@/components/ui/LoadingState';
import { ProvenanceLink } from '@/components/ui/ProvenanceLink';
import { StatusIndicator } from '@/components/ui/StatusIndicator';
import type {
  ApiAsset,
  ApiCoverageEntry,
  ApiFact,
  ApiManifest,
  ApiMission,
  ApiModel,
  ApiRef,
} from '@/types/api/manifest';
import type { CoveragePeriod } from '@/types/visualization/coverage';
import { assetMatches, missionMatches } from '@/features/explorer/filters';
import type { ExplorerFilters } from '@/features/explorer/filters';

/**
 * The coverage timeline is loaded on demand.
 *
 * The chart library is the largest thing the application ships; a reader who
 * opens a country and never reaches a coverage should not download it.
 */
const LazyCoverageTimeline = lazy(() =>
  import('@/components/visualization/CoverageTimeline').then((module) => ({
    default: module.CoverageTimeline,
  })),
);

function CoverageTimeline(props: {
  readonly title: string;
  readonly description?: string;
  readonly periods: readonly CoveragePeriod[];
  readonly height?: number;
}) {
  return (
    <Suspense fallback={<LoadingState label="Loading the coverage timeline…" />}>
      <LazyCoverageTimeline {...props} />
    </Suspense>
  );
}

export interface ExplorerContext {
  readonly manifest: ApiManifest;
  readonly filters: ExplorerFilters;
  readonly navigate: (path: string) => void;
  readonly countryName: (code: string) => string;
  readonly domainTitle: (id: string) => string;
}

// ------------------------------------------------------------------ fragments

function Refs({ refs }: { readonly refs: readonly ApiRef[] }) {
  if (refs.length === 0) {
    return null;
  }
  return (
    <span className="torne-explorer__refs">
      {refs.map((ref, index) => (
        <ProvenanceLink key={`${ref.kind}-${ref.target}-${index}`} reference={ref} />
      ))}
    </span>
  );
}

function FactList({
  facts,
  empty = 'Nothing recorded.',
}: {
  readonly facts: readonly ApiFact[];
  readonly empty?: string;
}) {
  if (facts.length === 0) {
    return <p className="torne-explorer__muted">{empty}</p>;
  }
  return (
    <div className="torne-explorer__facts">
      {facts.map((fact, index) => (
        <div className="torne-explorer__fact" key={`${fact.text.slice(0, 24)}-${index}`}>
          <p>{fact.text}</p>
          <Refs refs={fact.refs} />
        </div>
      ))}
    </div>
  );
}

function LinkButton({
  onClick,
  children,
}: {
  readonly onClick: () => void;
  readonly children: ReactNode;
}) {
  return (
    <button type="button" className="torne-explorer__link" onClick={onClick}>
      {children}
    </button>
  );
}

function StatusBadge({ status, rank }: { readonly status: string | null; readonly rank: number }) {
  return (
    <StatusIndicator status={status ?? 'not covered'} rank={rank} />
  );
}

// ---------------------------------------------------------------- normalisation

/**
 * The instant of a coverage bound.
 *
 * A period may be recorded as a year alone. A start is then the first day of
 * that year, and an end the last day: the bound is not invented, it is the
 * widest the year allows.
 */
export function coverageInstant(value: string | null, bound: 'start' | 'end'): string | null {
  if (value === null || value === '') {
    return null;
  }
  if (/^\d{4}$/.test(value)) {
    return bound === 'start' ? `${value}-01-01` : `${value}-12-31`;
  }
  return value;
}

/** The coverage entries as the timeline's periods. */
export function toCoveragePeriods(entries: readonly ApiCoverageEntry[]): CoveragePeriod[] {
  return entries.map((entry) => ({
    id: `${entry.subject_kind}:${entry.subject_id}`,
    subject: entry.title,
    kind: entry.subject_kind === 'surface_product' ? 'published' : 'observed',
    start: coverageInstant(entry.start, 'start'),
    end: coverageInstant(entry.end, 'end'),
    open: entry.open,
    provenance: entry.refs,
  }));
}

// ---------------------------------------------------------------------- views

function Overview({ context }: { readonly context: ExplorerContext }) {
  const { manifest, filters, navigate } = context;

  const countries = manifest.countries.map((country) => {
    const best = Math.max(...country.domains.map((domain) => domain.status_rank));
    const label = manifest.statuses.find((entry) => entry.rank === best)?.status ?? null;
    return (
      <div className="torne-explorer__row" key={country.country}>
        <LinkButton onClick={() => navigate(`/country/${country.country}`)}>
          {context.countryName(country.country)}
        </LinkButton>
        <StatusBadge status={label} rank={best} />
      </div>
    );
  });

  const regions = manifest.regions.map((region) => (
    <div key={region.region}>
      <div className="torne-explorer__row">
        <span>
          {region.region}-wide · {region.domain_ids.map(context.domainTitle).join(', ')}
        </span>
        <StatusIndicator status={region.status} rank={manifest.statuses.find((s) => s.status === region.status)?.rank ?? 0} />
      </div>
      <p className="torne-explorer__muted torne-explorer__small">
        From{' '}
        {region.mission_ids.map((id) => (
          <LinkButton key={id} onClick={() => navigate(`/mission/${id}`)}>
            {id}
          </LinkButton>
        ))}
      </p>
    </div>
  ));

  const executed = manifest.models.filter((model) => model.executed_on_real_data).length;

  return (
    <>
      <Breadcrumbs items={[{ label: 'Europe' }]} />
      <h2 className="torne-explorer__title">Europe</h2>
      <p className="torne-explorer__muted">
        Colours show the highest status a country's missions have reached — earned by evidence,
        never declared. Select a country, or explore a concept below.
      </p>

      <h3 className="torne-explorer__heading">Countries with missions</h3>
      {countries}

      <h3 className="torne-explorer__heading">Region-wide coverage</h3>
      {regions}

      <h3 className="torne-explorer__heading">Concepts</h3>
      <div className="torne-explorer__row">
        <LinkButton onClick={() => navigate('/coverage')}>Observation coverage</LinkButton>
        <span className="torne-explorer__muted">{manifest.coverage.length} periods</span>
      </div>
      <div className="torne-explorer__row">
        <LinkButton onClick={() => navigate('/models')}>Models and methods</LinkButton>
        <span className="torne-explorer__muted">
          {executed} of {manifest.models.length} run on real data
        </span>
      </div>
      <div className="torne-explorer__row">
        <LinkButton onClick={() => navigate('/results')}>Published results</LinkButton>
        <span className="torne-explorer__muted">
          {manifest.results.persisted.length} persisted
        </span>
      </div>

      <h3 className="torne-explorer__heading">Planned, not available</h3>
      {manifest.planned.map((planned) => (
        <p className="torne-explorer__muted torne-explorer__small" key={planned.feature}>
          {planned.feature} — needs {planned.needs}
        </p>
      ))}
      {filters.domain === '' && filters.status === '' && filters.kind === '' ? null : (
        <p className="torne-explorer__muted torne-explorer__small">
          The filters narrow the map and the lists; they never hide what a country holds.
        </p>
      )}
    </>
  );
}

function Uncovered({ name }: { readonly name: string }) {
  return (
    <>
      <Breadcrumbs items={[{ label: 'Europe' }, { label: name }]} />
      <h2 className="torne-explorer__title">{name}</h2>
      <p className="torne-explorer__muted">
        No mission has touched this country. Region-wide surface products may cover it; that
        coverage is not a national status.
      </p>
    </>
  );
}

function Country({
  context,
  code,
}: {
  readonly context: ExplorerContext;
  readonly code: string;
}) {
  const { manifest, navigate } = context;
  const summary = manifest.countries.find((country) => country.country === code);

  if (summary === undefined) {
    return <Uncovered name={context.countryName(code)} />;
  }

  const domains = summary.domains
    .filter((domain) => context.filters.domain === '' || domain.domain_id === context.filters.domain)
    .map((domain) => (
      <div key={domain.domain_id}>
        <div className="torne-explorer__row">
          <LinkButton onClick={() => navigate(`/country/${code}/domain/${domain.domain_id}`)}>
            {domain.title}
          </LinkButton>
          <StatusBadge status={domain.status} rank={domain.status_rank} />
        </div>
        {domain.status !== null ? (
          <p className="torne-explorer__muted torne-explorer__small">
            Status from{' '}
            {domain.status_from.map((id) => (
              <LinkButton key={id} onClick={() => navigate(`/mission/${id}`)}>
                {id}
              </LinkButton>
            ))}
          </p>
        ) : null}
      </div>
    ));

  const regional = manifest.regions.map((region) => (
    <div className="torne-explorer__row" key={region.region}>
      <span>
        {region.region}-wide · {region.domain_ids.map(context.domainTitle).join(', ')}
      </span>
      <StatusIndicator
        status={region.status}
        rank={manifest.statuses.find((entry) => entry.status === region.status)?.rank ?? 0}
      />
    </div>
  ));

  return (
    <>
      <Breadcrumbs
        items={[{ label: 'Europe', href: '/' }, { label: context.countryName(code) }]}
      />
      <h2 className="torne-explorer__title">{context.countryName(code)}</h2>

      <h3 className="torne-explorer__heading">Domains</h3>
      {domains}

      <h3 className="torne-explorer__heading">Region-wide, not national</h3>
      {regional}

      <h3 className="torne-explorer__heading">Published results</h3>
      <ResultsSummary context={context} />
    </>
  );
}

function ResultsSummary({ context }: { readonly context: ExplorerContext }) {
  const { manifest } = context;
  if (manifest.results.persisted.length > 0) {
    return <p>{manifest.results.persisted.length} persisted record(s).</p>;
  }
  return <p className="torne-explorer__gap">{manifest.results.gap}</p>;
}

function Domain({
  context,
  code,
  domainId,
}: {
  readonly context: ExplorerContext;
  readonly code: string;
  readonly domainId: string;
}) {
  const { manifest, filters, navigate } = context;
  const summary = manifest.countries.find((country) => country.country === code);
  const domain = summary?.domains.find((entry) => entry.domain_id === domainId);

  if (domain === undefined) {
    return <Country context={context} code={code} />;
  }

  const missions = domain.mission_ids
    .map((id) => manifest.missions.find((mission) => mission.mission_id === id))
    .filter((mission): mission is ApiMission => mission !== undefined)
    .filter((mission) => missionMatches(mission, filters, manifest.statuses));

  const assets = domain.asset_ids
    .map((id) => manifest.assets.find((asset) => asset.asset_id === id))
    .filter((asset): asset is ApiAsset => asset !== undefined)
    .filter((asset) => assetMatches(asset, filters, manifest.missions, manifest.statuses));

  const coverage = manifest.coverage.filter(
    (entry) => entry.country === code && entry.domain_id === domain.domain_id,
  );

  return (
    <>
      <Breadcrumbs
        items={[
          { label: 'Europe', href: '/' },
          { label: context.countryName(code), href: `/country/${code}` },
          { label: domain.title },
        ]}
      />
      <h2 className="torne-explorer__title">
        {domain.title} · {context.countryName(code)}
      </h2>
      <StatusBadge status={domain.status} rank={domain.status_rank} />

      <h3 className="torne-explorer__heading">Missions</h3>
      {missions.length === 0 ? (
        <p className="torne-explorer__muted">None matches the filters.</p>
      ) : (
        missions.map((mission) => (
          <div key={mission.mission_id}>
            <div className="torne-explorer__row">
              <LinkButton onClick={() => navigate(`/mission/${mission.mission_id}`)}>
                {mission.mission_id}
              </LinkButton>
              <StatusBadge status={mission.status} rank={mission.status_rank} />
            </div>
            <p className="torne-explorer__muted torne-explorer__small">{mission.title}</p>
          </div>
        ))
      )}

      <h3 className="torne-explorer__heading">Sources</h3>
      {domain.source_ids.length === 0 ? (
        <p className="torne-explorer__muted">None.</p>
      ) : (
        domain.source_ids.map((id) => {
          const source = manifest.sources.find((entry) => entry.source_id === id);
          return (
            <div className="torne-explorer__row" key={id}>
              <LinkButton onClick={() => navigate(`/source/${id}`)}>{source?.title ?? id}</LinkButton>
            </div>
          );
        })
      )}

      <h3 className="torne-explorer__heading">Physical assets</h3>
      {assets.length === 0 ? (
        <p className="torne-explorer__muted">None touched yet.</p>
      ) : (
        assets.map((asset) => (
          <div className="torne-explorer__row" key={asset.asset_id}>
            <LinkButton onClick={() => navigate(`/asset/${asset.asset_id}`)}>{asset.name}</LinkButton>
            <span className="torne-explorer__muted">{asset.kind}</span>
          </div>
        ))
      )}

      <h3 className="torne-explorer__heading">Observation coverage</h3>
      {coverage.length === 0 ? (
        <p className="torne-explorer__muted">No measured period.</p>
      ) : (
        <CoverageTimeline
          title={`Observation coverage — ${domain.title}`}
          description="Periods that observations cover — not periods for which knowledge was produced."
          periods={toCoveragePeriods(coverage)}
        />
      )}

      <h3 className="torne-explorer__heading">Models and methods</h3>
      {domain.model_keys.length === 0 ? (
        <p className="torne-explorer__muted">None.</p>
      ) : (
        domain.model_keys.map((key) => {
          const model = manifest.models.find((entry) => entry.key === key);
          return model === undefined ? null : <ModelRow key={key} model={model} context={context} />;
        })
      )}

      <h3 className="torne-explorer__heading">Published results</h3>
      <ResultsSummary context={context} />
    </>
  );
}

function ModelRow({ model, context }: { readonly model: ApiModel; readonly context: ExplorerContext }) {
  const state = model.executed_on_real_data
    ? 'run on real data'
    : 'implemented, not run on real data';
  return (
    <div className="torne-explorer__row">
      <LinkButton onClick={() => context.navigate(`/models/${model.key}`)}>{model.title}</LinkButton>
      <span className="torne-explorer__muted torne-explorer__small">{state}</span>
    </div>
  );
}

function Mission({
  context,
  missionId,
}: {
  readonly context: ExplorerContext;
  readonly missionId: string;
}) {
  const { manifest, navigate } = context;
  const mission = manifest.missions.find((entry) => entry.mission_id === missionId);

  if (mission === undefined) {
    return <Overview context={context} />;
  }

  const country = mission.countries[0];
  const trail = [
    { label: 'Europe', href: '/' },
    ...(country !== undefined
      ? [{ label: context.countryName(country), href: `/country/${country}` }]
      : []),
    { label: mission.mission_id },
  ];

  return (
    <>
      <Breadcrumbs items={trail} />
      <h2 className="torne-explorer__title">{mission.mission_id}</h2>
      <StatusBadge status={mission.status} rank={mission.status_rank} />
      <p>{mission.title}</p>
      <p className="torne-explorer__muted torne-explorer__small">Status supported by</p>
      <Refs refs={mission.status_basis} />

      <h3 className="torne-explorer__heading">Question</h3>
      <p>{mission.question}</p>

      <h3 className="torne-explorer__heading">Produced</h3>
      <FactList facts={mission.produced} />

      <h3 className="torne-explorer__heading">Not established</h3>
      <FactList facts={mission.not_established} />

      <h3 className="torne-explorer__heading">Sources</h3>
      {mission.source_ids.length === 0 ? (
        <p className="torne-explorer__muted">None.</p>
      ) : (
        mission.source_ids.map((id) => {
          const source = manifest.sources.find((entry) => entry.source_id === id);
          return (
            <div className="torne-explorer__row" key={id}>
              <LinkButton onClick={() => navigate(`/source/${id}`)}>{source?.title ?? id}</LinkButton>
            </div>
          );
        })
      )}

      <h3 className="torne-explorer__heading">Physical assets</h3>
      {mission.asset_ids.length === 0 ? (
        <p className="torne-explorer__muted">None touched.</p>
      ) : (
        mission.asset_ids.map((id) => {
          const asset = manifest.assets.find((entry) => entry.asset_id === id);
          return (
            <div className="torne-explorer__row" key={id}>
              <LinkButton onClick={() => navigate(`/asset/${id}`)}>{asset?.name ?? id}</LinkButton>
            </div>
          );
        })
      )}

      <h3 className="torne-explorer__heading">Models and methods</h3>
      {mission.model_keys.length === 0 ? (
        <p className="torne-explorer__muted">None.</p>
      ) : (
        mission.model_keys.map((key) => {
          const model = manifest.models.find((entry) => entry.key === key);
          return model === undefined ? null : <ModelRow key={key} model={model} context={context} />;
        })
      )}

      {mission.domain_ids.includes('earth_observation') ? (
        <>
          <h3 className="torne-explorer__heading">Observation coverage</h3>
          <LinkButton onClick={() => navigate('/coverage')}>Surface product coverage</LinkButton>
        </>
      ) : null}
    </>
  );
}

function Asset({
  context,
  assetId,
}: {
  readonly context: ExplorerContext;
  readonly assetId: string;
}) {
  const { manifest, navigate } = context;
  const asset = manifest.assets.find((entry) => entry.asset_id === assetId);

  if (asset === undefined) {
    return <Overview context={context} />;
  }

  const source = manifest.sources.find((entry) => entry.source_id === asset.source_id);
  const coverage = manifest.coverage.filter((entry) => entry.subject_id === asset.asset_id);

  const trail = [
    { label: 'Europe', href: '/' },
    ...(asset.country !== null
      ? [
          {
            label: context.countryName(asset.country),
            href: `/country/${asset.country}`,
          },
          {
            label: context.domainTitle(asset.domain_id),
            href: `/country/${asset.country}/domain/${asset.domain_id}`,
          },
        ]
      : []),
    { label: asset.name },
  ];

  return (
    <>
      <Breadcrumbs items={trail} />
      <h2 className="torne-explorer__title">{asset.name}</h2>
      <p className="torne-explorer__muted">
        {asset.kind} · {asset.asset_id}
      </p>

      <div className="torne-explorer__card">
        <dl>
          <dt>Source</dt>
          <dd>
            <LinkButton onClick={() => navigate(`/source/${asset.source_id}`)}>
              {source?.title ?? asset.source_id}
            </LinkButton>
          </dd>
          <dt>Location</dt>
          <dd>
            {asset.point === null
              ? '—'
              : `${asset.point[1].toFixed(4)}, ${asset.point[0].toFixed(4)}`}{' '}
            <Refs refs={[asset.location_ref]} />
          </dd>
        </dl>
      </div>

      <h3 className="torne-explorer__heading">Observation coverage</h3>
      {coverage.length === 0 ? (
        <p className="torne-explorer__muted">Not measured.</p>
      ) : (
        <CoverageTimeline
          title={`Observation coverage — ${asset.name}`}
          periods={toCoveragePeriods(coverage)}
        />
      )}

      <h3 className="torne-explorer__heading">What was measured</h3>
      <FactList facts={asset.facts} />

      <h3 className="torne-explorer__heading">Missions</h3>
      {asset.mission_ids.map((id) => {
        const mission = manifest.missions.find((entry) => entry.mission_id === id);
        return (
          <div className="torne-explorer__row" key={id}>
            <LinkButton onClick={() => navigate(`/mission/${id}`)}>{id}</LinkButton>
            <StatusBadge status={mission?.status ?? null} rank={mission?.status_rank ?? 0} />
          </div>
        );
      })}
    </>
  );
}

function Source({
  context,
  sourceId,
}: {
  readonly context: ExplorerContext;
  readonly sourceId: string;
}) {
  const { manifest, navigate } = context;
  const source = manifest.sources.find((entry) => entry.source_id === sourceId);

  if (source === undefined) {
    return <Overview context={context} />;
  }

  return (
    <>
      <Breadcrumbs items={[{ label: 'Europe', href: '/' }, { label: source.title }]} />
      <h2 className="torne-explorer__title">{source.title}</h2>
      <p className="torne-explorer__muted">
        {source.source_id} · {context.domainTitle(source.domain_id)}
      </p>

      <div className="torne-explorer__card">
        <dl>
          <dt>Publication class</dt>
          <dd>
            <Badge tone={source.publication_class === null ? 'neutral' : 'info'}>
              {source.publication_class?.toUpperCase() ?? 'not established'}
            </Badge>
          </dd>
          <dt>Adapter</dt>
          <dd>
            <Refs refs={[source.adapter_ref]} />
          </dd>
          <dt>Qualified in</dt>
          <dd>
            <Refs refs={[source.qualified_in]} />
          </dd>
        </dl>
      </div>

      <h3 className="torne-explorer__heading">Established behaviour</h3>
      <FactList facts={source.facts} />

      <h3 className="torne-explorer__heading">Used by</h3>
      {source.mission_ids.length === 0 ? (
        <p className="torne-explorer__muted">No mission.</p>
      ) : (
        source.mission_ids.map((id) => (
          <div className="torne-explorer__row" key={id}>
            <LinkButton onClick={() => navigate(`/mission/${id}`)}>{id}</LinkButton>
          </div>
        ))
      )}
    </>
  );
}

function Models({ context, key }: { readonly context: ExplorerContext; readonly key?: string }) {
  const { manifest, navigate } = context;

  if (key === undefined) {
    return (
      <>
        <Breadcrumbs items={[{ label: 'Europe', href: '/' }, { label: 'Models and methods' }]} />
        <h2 className="torne-explorer__title">Models and methods</h2>
        <p className="torne-explorer__muted">
          Identities and versions are read from the code. "Run on real data" requires recorded
          evidence.
        </p>
        {manifest.models.map((model) => (
          <div key={model.key}>
            <ModelRow model={model} context={context} />
            <p className="torne-explorer__muted torne-explorer__small">{model.kind}</p>
          </div>
        ))}
      </>
    );
  }

  const model = manifest.models.find((entry) => entry.key === key);
  if (model === undefined) {
    return <Models context={context} />;
  }

  return (
    <>
      <Breadcrumbs
        items={[
          { label: 'Europe', href: '/' },
          { label: 'Models and methods', href: '/models' },
          { label: model.title },
        ]}
      />
      <h2 className="torne-explorer__title">{model.title}</h2>
      <p className="torne-explorer__muted">{model.kind}</p>

      <div className="torne-explorer__card">
        <dl>
          <dt>Identity</dt>
          <dd>
            {model.identity} <Refs refs={[model.identity_ref]} />
          </dd>
          <dt>Version</dt>
          <dd>
            {model.version ?? 'not exposed by the module'}{' '}
            {model.version_ref === null ? null : <Refs refs={[model.version_ref]} />}
          </dd>
        </dl>
      </div>

      <h3 className="torne-explorer__heading">Runs on real data</h3>
      <FactList facts={model.runs} empty="Implemented and tested; never run on real data." />

      <h3 className="torne-explorer__heading">Missions</h3>
      {model.mission_ids.length === 0 ? (
        <p className="torne-explorer__muted">No mission.</p>
      ) : (
        model.mission_ids.map((id) => (
          <div className="torne-explorer__row" key={id}>
            <LinkButton onClick={() => navigate(`/mission/${id}`)}>{id}</LinkButton>
          </div>
        ))
      )}
    </>
  );
}

function Coverage({ context }: { readonly context: ExplorerContext }) {
  const { manifest, filters } = context;
  const filtered = manifest.coverage.filter(
    (entry) => filters.domain === '' || entry.domain_id === filters.domain,
  );
  const assets = filtered.filter((entry) => entry.subject_kind === 'asset');
  const products = filtered.filter((entry) => entry.subject_kind === 'surface_product');

  return (
    <>
      <Breadcrumbs items={[{ label: 'Europe', href: '/' }, { label: 'Observation coverage' }]} />
      <h2 className="torne-explorer__title">Observation coverage</h2>
      <p className="torne-explorer__muted">
        Periods that observations cover — not periods for which knowledge was produced.
      </p>

      {filtered.length === 0 ? (
        <EmptyState
          title="Nothing matches the filters"
          description="Reset the filters to see every period the repository has established."
        />
      ) : (
        <CoverageTimeline
          title="Coverage of every subject"
          description="An observed period, a published period, and the gaps between them."
          periods={toCoveragePeriods(filtered)}
          height={320}
        />
      )}

      <h3 className="torne-explorer__heading">Stations</h3>
      <p className="torne-explorer__muted torne-explorer__small">{assets.length} periods</p>

      <h3 className="torne-explorer__heading">Surface products (Europe-wide)</h3>
      <p className="torne-explorer__muted torne-explorer__small">{products.length} periods</p>
    </>
  );
}

function Results({ context }: { readonly context: ExplorerContext }) {
  const { manifest, navigate } = context;
  const runs = manifest.results.runs_not_persisted.map((run) => (
    <div className="torne-explorer__card" key={run.mission_id}>
      <div className="torne-explorer__row">
        <LinkButton onClick={() => navigate(`/mission/${run.mission_id}`)}>{run.mission_id}</LinkButton>
        <StatusIndicator status={run.status} rank={manifest.statuses.find((s) => s.status === run.status)?.rank ?? 0} />
      </div>
      <FactList facts={run.produced} />
    </div>
  ));

  return (
    <>
      <Breadcrumbs items={[{ label: 'Europe', href: '/' }, { label: 'Published results' }]} />
      <h2 className="torne-explorer__title">Published results</h2>
      <ResultsSummary context={context} />

      <h3 className="torne-explorer__heading">Produced in a run, not persisted</h3>
      {runs.length === 0 ? <p className="torne-explorer__muted">None.</p> : runs}
    </>
  );
}

/** The legend of the map: what the colours mean. */
export function statusLegend(manifest: ApiManifest) {
  const items = [
    { label: 'not covered', color: 'var(--science-status-0)', shape: 'square' as const },
    ...manifest.statuses.map((entry) => ({
      label: entry.status,
      color: `var(--science-status-${entry.rank})`,
      shape: 'square' as const,
    })),
    { label: 'station', color: 'var(--map-marker)', shape: 'circle' as const },
  ];
  return <Legend title="What the colours mean" items={items} />;
}

export {
  Asset,
  Coverage,
  Country,
  Domain,
  Mission,
  Models,
  Overview,
  Results,
  Source,
  Uncovered,
};
