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
 *
 * Every view has the same anatomy, so that a reader who has learned one page
 * can read the next: a breadcrumb trail, a page header — what kind of page
 * this is, what it is called, what it shows — a status strip when the page
 * has a status, and then sections whose heading is an eyebrow.
 *
 * The hierarchy is carried by type, not by colour. A claim, the evidence
 * behind it, and a link to another page must never look the same thing.
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
  ApiCountrySummary,
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

/**
 * The references that back a fact or a status.
 *
 * They are rendered as quiet chips: the reader must see that the evidence is
 * there, without the evidence competing with the claim it supports.
 */
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

/**
 * The header of a page.
 *
 * The eyebrow names the kind of thing being read — a country, a mission, a
 * model — so the reader knows what they are looking at before they read the
 * title. The lede says what the page shows, in one sentence.
 *
 * This block is the only place in the explorer where a shadow is allowed: it
 * is the one element that lifts off the page it is printed on.
 */
function PageHeader({
  eyebrow,
  title,
  lede,
  meta,
}: {
  readonly eyebrow: string;
  readonly title: string;
  readonly lede?: string;
  readonly meta?: ReactNode;
}) {
  return (
    <header className="torne-explorer__page-header">
      <p className="torne-explorer__eyebrow">{eyebrow}</p>
      <h2 className="torne-explorer__title">{title}</h2>
      {lede !== undefined ? <p className="torne-explorer__lede">{lede}</p> : null}
      {meta !== undefined ? <p className="torne-explorer__meta">{meta}</p> : null}
    </header>
  );
}

/**
 * The status of the page, and the evidence that supports it.
 *
 * A status is never shown on its own: the references that earned it sit
 * beside it, so a reader can always check the claim against its evidence.
 */
function StatusStrip({
  status,
  rank,
  evidence,
}: {
  readonly status: string;
  readonly rank: number;
  readonly evidence?: ReactNode;
}) {
  return (
    <div className="torne-explorer__status">
      <p className="torne-explorer__eyebrow">Status</p>
      <div className="torne-explorer__status-value">
        <StatusIndicator status={status} rank={rank} />
        {evidence !== undefined ? (
          <span className="torne-explorer__status-evidence">
            <span className="torne-explorer__eyebrow">Status supported by</span>
            {evidence}
          </span>
        ) : null}
      </div>
    </div>
  );
}

/**
 * A section of the page.
 *
 * The heading is an eyebrow — small, uppercase, quiet — because the reader
 * navigates by it, not by its size. It stays a real heading element, so the
 * page can still be skimmed through the heading list of a screen reader.
 */
function Section({
  title,
  note,
  children,
}: {
  readonly title: string;
  readonly note?: ReactNode;
  readonly children?: ReactNode;
}) {
  return (
    <section className="torne-explorer__section">
      <div className="torne-explorer__section-heading">
        <h3 className="torne-explorer__section-title">{title}</h3>
        {note !== undefined ? <span className="torne-explorer__section-note">{note}</span> : null}
      </div>
      {children !== undefined ? (
        <div className="torne-explorer__section-body">{children}</div>
      ) : null}
    </section>
  );
}

/**
 * A link that navigates inside the explorer.
 *
 * Two looks, because a link has two jobs: inside a sentence it is an accent
 * affordance, and as the name of an entity it is the title of a row.
 */
function LinkButton({
  onClick,
  children,
  variant = 'inline',
  className,
}: {
  readonly onClick: () => void;
  readonly children: ReactNode;
  readonly variant?: 'inline' | 'entity';
  readonly className?: string | undefined;
}) {
  const base = variant === 'entity' ? 'torne-explorer__entity' : 'torne-explorer__link';
  return (
    <button
      type="button"
      className={className === undefined ? base : `${base} ${className}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

/**
 * A row of the reading column: one entity of the catalogue.
 *
 * The name is the title of the row, not a link inside a sentence, so it is
 * set in the body type and takes the accent only on hover; the identifier
 * beside it is set in the mono face, because it is a code and not a word. The
 * status, when the row carries one, sits on the right, where the eye
 * compares.
 *
 * The evidence line under the row carries the references that support the
 * row's claim. A status is never shown without them.
 */
function EntityRow({
  name,
  code = false,
  identifier,
  meta,
  evidence,
  status,
  rank,
  onOpen,
}: {
  readonly name: string;
  readonly code?: boolean;
  readonly identifier?: ReactNode;
  readonly meta?: ReactNode;
  readonly evidence?: ReactNode;
  readonly status?: string;
  readonly rank?: number;
  readonly onOpen?: () => void;
}) {
  return (
    <div className="torne-explorer__row">
      <div className="torne-explorer__row-main">
        <span className="torne-explorer__row-title">
          {onOpen === undefined ? (
            <span className="torne-explorer__row-name">{name}</span>
          ) : (
            <LinkButton
              onClick={onOpen}
              variant="entity"
              className={code ? 'torne-explorer__entity--code' : undefined}
            >
              {name}
            </LinkButton>
          )}
          {identifier !== undefined ? (
            <span className="torne-explorer__row-id">{identifier}</span>
          ) : null}
        </span>
        {meta !== undefined ? <span className="torne-explorer__row-meta">{meta}</span> : null}
        {evidence !== undefined ? (
          <span className="torne-explorer__row-evidence">{evidence}</span>
        ) : null}
      </div>
      {status !== undefined ? (
        <span className="torne-explorer__row-status">
          <StatusBadge status={status} rank={rank ?? 0} />
        </span>
      ) : null}
    </div>
  );
}

/**
 * The missions that support a status, written as links.
 *
 * They are the evidence of a claim, so they stand next to it rather than in a
 * list further down the page.
 */
function MissionLinks({
  ids,
  navigate,
}: {
  readonly ids: readonly string[];
  readonly navigate: (path: string) => void;
}) {
  return (
    <>
      {ids.map((id) => (
        <LinkButton key={id} onClick={() => navigate(`/mission/${id}`)}>
          {id}
        </LinkButton>
      ))}
    </>
  );
}

/**
 * The facts of an entity, each with the evidence that supports it.
 *
 * A fact is never shown bare: it is an evidence block, and the references
 * that back it sit inside the block.
 */
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

// --------------------------------------------------------------------- status

/**
 * The status a country has earned, and the missions that earned it.
 *
 * It is the highest status among the country's own domains — the same
 * derivation the map and the overview use — and the supporting missions are
 * the ones those domains name. A status is never shown without them.
 */
function countryStatus(summary: ApiCountrySummary, manifest: ApiManifest) {
  const best =
    summary.domains.length === 0
      ? 0
      : Math.max(...summary.domains.map((domain) => domain.status_rank));
  const status =
    best <= 0
      ? 'not covered'
      : (manifest.statuses.find((entry) => entry.rank === best)?.status ?? 'not covered');
  const missions = summary.domains
    .filter((domain) => domain.status_rank === best && domain.status !== null)
    .flatMap((domain) => domain.status_from);
  return { status, rank: best, missions };
}

// ---------------------------------------------------------------------- views

function Overview({ context }: { readonly context: ExplorerContext }) {
  const { manifest, filters, navigate } = context;

  const countries = manifest.countries.map((country) => {
    const earned = countryStatus(country, manifest);
    return (
      <EntityRow
        key={country.country}
        name={context.countryName(country.country)}
        onOpen={() => navigate(`/country/${country.country}`)}
        status={earned.status}
        rank={earned.rank}
      />
    );
  });

  const regions = manifest.regions.map((region) => (
    <EntityRow
      key={region.region}
      name={`${region.region}-wide`}
      meta={region.domain_ids.map(context.domainTitle).join(', ')}
      evidence={
        <>
          From{' '}
          <MissionLinks ids={region.mission_ids} navigate={navigate} />
        </>
      }
      status={region.status}
      rank={manifest.statuses.find((s) => s.status === region.status)?.rank ?? 0}
    />
  ));

  const executed = manifest.models.filter((model) => model.executed_on_real_data).length;

  const concepts = [
    {
      key: 'coverage',
      name: 'Observation coverage',
      path: '/coverage',
      meta: `${manifest.coverage.length} periods`,
    },
    {
      key: 'models',
      name: 'Models and methods',
      path: '/models',
      meta: `${executed} of ${manifest.models.length} run on real data`,
    },
    {
      key: 'results',
      name: 'Published results',
      path: '/results',
      meta: `${manifest.results.persisted.length} persisted`,
    },
  ];

  return (
    <>
      <Breadcrumbs items={[{ label: 'Europe' }]} />
      <PageHeader
        eyebrow="OVERVIEW"
        title="Europe"
        lede="Colours show the highest status a country's missions have reached — earned by evidence, never declared. Select a country, or explore a concept below."
      />

      <Section title="Countries with missions">
        <div className="torne-explorer__entity-list">{countries}</div>
      </Section>

      <Section title="Region-wide coverage">
        <div className="torne-explorer__entity-list">{regions}</div>
      </Section>

      <Section title="Concepts">
        <div className="torne-explorer__entity-list">
          {concepts.map((concept) => (
            <EntityRow
              key={concept.key}
              name={concept.name}
              meta={concept.meta}
              onOpen={() => navigate(concept.path)}
            />
          ))}
        </div>
      </Section>

      <Section title="Planned, not available">
        <ul className="torne-explorer__planned">
          {manifest.planned.map((planned) => (
            <li className="torne-explorer__planned-item" key={planned.feature}>
              <span className="torne-explorer__planned-feature">{planned.feature}</span>
              {' — needs '}
              <span className="torne-explorer__planned-needs">{planned.needs}</span>
            </li>
          ))}
        </ul>
      </Section>

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
      <PageHeader
        eyebrow="COUNTRY"
        title={name}
        lede="No mission has touched this country."
      />
      <StatusStrip status="not covered" rank={0} />
      <Section title="Region-wide coverage">
        <p className="torne-explorer__muted">
          Region-wide surface products may cover it; that coverage is not a national status.
        </p>
      </Section>
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

  const earned = countryStatus(summary, manifest);

  const domains = summary.domains
    .filter((domain) => context.filters.domain === '' || domain.domain_id === context.filters.domain)
    .map((domain) => (
      <EntityRow
        key={domain.domain_id}
        name={domain.title}
        onOpen={() => navigate(`/country/${code}/domain/${domain.domain_id}`)}
        status={domain.status ?? 'not covered'}
        rank={domain.status_rank}
        evidence={
          domain.status !== null && domain.status_from.length > 0 ? (
            <>
              Status from{' '}
              <MissionLinks ids={domain.status_from} navigate={navigate} />
            </>
          ) : undefined
        }
      />
    ));

  const regional = manifest.regions.map((region) => (
    <EntityRow
      key={region.region}
      name={`${region.region}-wide`}
      meta={region.domain_ids.map(context.domainTitle).join(', ')}
      evidence={
        <>
          From{' '}
          <MissionLinks ids={region.mission_ids} navigate={navigate} />
        </>
      }
      status={region.status}
      rank={manifest.statuses.find((entry) => entry.status === region.status)?.rank ?? 0}
    />
  ));

  return (
    <>
      <Breadcrumbs
        items={[{ label: 'Europe', href: '/' }, { label: context.countryName(code) }]}
      />
      <PageHeader
        eyebrow="COUNTRY"
        title={context.countryName(code)}
        lede="What this country's own missions established, domain by domain, and what they did not."
      />
      <StatusStrip
        status={earned.status}
        rank={earned.rank}
        evidence={
          earned.missions.length > 0 ? (
            <MissionLinks ids={earned.missions} navigate={navigate} />
          ) : undefined
        }
      />

      <Section title="Domains">
        <div className="torne-explorer__entity-list">{domains}</div>
      </Section>

      <Section title="Region-wide, not national">
        <div className="torne-explorer__entity-list">{regional}</div>
      </Section>

      <Section title="Published results">
        <ResultsSummary context={context} />
      </Section>
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
      <PageHeader
        eyebrow="DOMAIN"
        title={`${domain.title} · ${context.countryName(code)}`}
        lede="The missions that worked on this domain here, the sources they read, and the coverage they measured."
      />
      <StatusStrip
        status={domain.status ?? 'not covered'}
        rank={domain.status_rank}
        evidence={
          domain.status_from.length > 0 ? (
            <MissionLinks ids={domain.status_from} navigate={navigate} />
          ) : undefined
        }
      />

      <Section title="Missions">
        {missions.length === 0 ? (
          <p className="torne-explorer__muted">None matches the filters.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {missions.map((mission) => (
              <EntityRow
                key={mission.mission_id}
                name={mission.mission_id}
                code
                meta={mission.title}
                onOpen={() => navigate(`/mission/${mission.mission_id}`)}
                status={mission.status}
                rank={mission.status_rank}
              />
            ))}
          </div>
        )}
      </Section>

      <Section title="Sources">
        {domain.source_ids.length === 0 ? (
          <p className="torne-explorer__muted">None.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {domain.source_ids.map((id) => {
              const source = manifest.sources.find((entry) => entry.source_id === id);
              return (
                <EntityRow
                  key={id}
                  name={source?.title ?? id}
                  onOpen={() => navigate(`/source/${id}`)}
                />
              );
            })}
          </div>
        )}
      </Section>

      <Section title="Physical assets">
        {assets.length === 0 ? (
          <p className="torne-explorer__muted">None touched yet.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {assets.map((asset) => (
              <EntityRow
                key={asset.asset_id}
                name={asset.name}
                identifier={asset.asset_id}
                meta={asset.kind}
                onOpen={() => navigate(`/asset/${asset.asset_id}`)}
              />
            ))}
          </div>
        )}
      </Section>

      <Section title="Observation coverage">
        {coverage.length === 0 ? (
          <p className="torne-explorer__muted">No measured period.</p>
        ) : (
          <CoverageTimeline
            title={`Observation coverage — ${domain.title}`}
            description="Periods that observations cover — not periods for which knowledge was produced."
            periods={toCoveragePeriods(coverage)}
          />
        )}
      </Section>

      <Section title="Models and methods">
        {domain.model_keys.length === 0 ? (
          <p className="torne-explorer__muted">None.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {domain.model_keys.map((key) => {
              const model = manifest.models.find((entry) => entry.key === key);
              return model === undefined ? null : <ModelRow key={key} model={model} context={context} />;
            })}
          </div>
        )}
      </Section>

      <Section title="Published results">
        <ResultsSummary context={context} />
      </Section>
    </>
  );
}

/**
 * A model in a list.
 *
 * Whether the model was run on real data is the fact a reader comes for, so
 * it stands on the row itself; the kind of model is the quieter context.
 */
function ModelRow({
  model,
  context,
  withKind = false,
}: {
  readonly model: ApiModel;
  readonly context: ExplorerContext;
  readonly withKind?: boolean;
}) {
  const state = model.executed_on_real_data
    ? 'run on real data'
    : 'implemented, not run on real data';
  return (
    <EntityRow
      name={model.title}
      identifier={model.key}
      meta={withKind ? `${state} · ${model.kind}` : state}
      onOpen={() => context.navigate(`/models/${model.key}`)}
    />
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
      <PageHeader eyebrow="MISSION" title={mission.mission_id} lede={mission.title} />
      <StatusStrip
        status={mission.status}
        rank={mission.status_rank}
        evidence={mission.status_basis.length > 0 ? <Refs refs={mission.status_basis} /> : undefined}
      />

      <Section title="Question">
        <p>{mission.question}</p>
      </Section>

      <Section title="Produced">
        <FactList facts={mission.produced} />
      </Section>

      <Section title="Not established">
        <FactList facts={mission.not_established} />
      </Section>

      <Section title="Sources">
        {mission.source_ids.length === 0 ? (
          <p className="torne-explorer__muted">None.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {mission.source_ids.map((id) => {
              const source = manifest.sources.find((entry) => entry.source_id === id);
              return (
                <EntityRow
                  key={id}
                  name={source?.title ?? id}
                  onOpen={() => navigate(`/source/${id}`)}
                />
              );
            })}
          </div>
        )}
      </Section>

      <Section title="Physical assets">
        {mission.asset_ids.length === 0 ? (
          <p className="torne-explorer__muted">None touched.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {mission.asset_ids.map((id) => {
              const asset = manifest.assets.find((entry) => entry.asset_id === id);
              return (
                <EntityRow
                  key={id}
                  name={asset?.name ?? id}
                  onOpen={() => navigate(`/asset/${id}`)}
                />
              );
            })}
          </div>
        )}
      </Section>

      <Section title="Models and methods">
        {mission.model_keys.length === 0 ? (
          <p className="torne-explorer__muted">None.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {mission.model_keys.map((key) => {
              const model = manifest.models.find((entry) => entry.key === key);
              return model === undefined ? null : <ModelRow key={key} model={model} context={context} />;
            })}
          </div>
        )}
      </Section>

      {mission.domain_ids.includes('earth_observation') ? (
        <Section title="Observation coverage">
          <LinkButton onClick={() => navigate('/coverage')}>Surface product coverage</LinkButton>
        </Section>
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
      <PageHeader
        eyebrow="ASSET"
        title={asset.name}
        lede="What was measured here, and which missions touched it."
        meta={`${asset.kind} · ${asset.asset_id}`}
      />

      <Section title="Details">
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
              {asset.point === null ? (
                '—'
              ) : (
                <span className="torne-explorer__code">
                  {`${asset.point[1].toFixed(4)}, ${asset.point[0].toFixed(4)}`}
                </span>
              )}{' '}
              <Refs refs={[asset.location_ref]} />
            </dd>
          </dl>
        </div>
      </Section>

      <Section title="Observation coverage">
        {coverage.length === 0 ? (
          <p className="torne-explorer__muted">Not measured.</p>
        ) : (
          <CoverageTimeline
            title={`Observation coverage — ${asset.name}`}
            periods={toCoveragePeriods(coverage)}
          />
        )}
      </Section>

      <Section title="What was measured">
        <FactList facts={asset.facts} />
      </Section>

      <Section title="Missions">
        <div className="torne-explorer__entity-list">
          {asset.mission_ids.map((id) => {
            const mission = manifest.missions.find((entry) => entry.mission_id === id);
            return (
              <EntityRow
                key={id}
                name={id}
                code
                onOpen={() => navigate(`/mission/${id}`)}
                status={mission?.status ?? 'not covered'}
                rank={mission?.status_rank ?? 0}
              />
            );
          })}
        </div>
      </Section>
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
      <PageHeader
        eyebrow="SOURCE"
        title={source.title}
        lede="What this source established, and which missions read it."
        meta={`${source.source_id} · ${context.domainTitle(source.domain_id)}`}
      />

      <Section title="Details">
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
      </Section>

      <Section title="Established behaviour">
        <FactList facts={source.facts} />
      </Section>

      <Section title="Used by">
        {source.mission_ids.length === 0 ? (
          <p className="torne-explorer__muted">No mission.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {source.mission_ids.map((id) => (
              <EntityRow
                key={id}
                name={id}
                code
                onOpen={() => navigate(`/mission/${id}`)}
              />
            ))}
          </div>
        )}
      </Section>
    </>
  );
}

function Models({ context, key }: { readonly context: ExplorerContext; readonly key?: string }) {
  const { manifest, navigate } = context;

  if (key === undefined) {
    return (
      <>
        <Breadcrumbs items={[{ label: 'Europe', href: '/' }, { label: 'Models and methods' }]} />
        <PageHeader
          eyebrow="MODELS"
          title="Models and methods"
          lede={
            'Identities and versions are read from the code. "Run on real data" requires recorded evidence.'
          }
        />
        <Section title="Catalogue">
          <div className="torne-explorer__entity-list">
            {manifest.models.map((model) => (
              <ModelRow key={model.key} model={model} context={context} withKind />
            ))}
          </div>
        </Section>
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
      <PageHeader
        eyebrow="MODEL"
        title={model.title}
        lede="The identity, the version, and the runs this model has recorded on real data."
      />

      <Section title="Details">
        <div className="torne-explorer__card">
          <dl>
            <dt>Kind</dt>
            <dd>{model.kind}</dd>
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
      </Section>

      <Section title="Runs on real data">
        <FactList facts={model.runs} empty="Implemented and tested; never run on real data." />
      </Section>

      <Section title="Missions">
        {model.mission_ids.length === 0 ? (
          <p className="torne-explorer__muted">No mission.</p>
        ) : (
          <div className="torne-explorer__entity-list">
            {model.mission_ids.map((id) => (
              <EntityRow
                key={id}
                name={id}
                code
                onOpen={() => navigate(`/mission/${id}`)}
              />
            ))}
          </div>
        )}
      </Section>
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
      <PageHeader
        eyebrow="COVERAGE"
        title="Observation coverage"
        lede="Periods that observations cover — not periods for which knowledge was produced."
      />

      <Section title="Timeline">
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
      </Section>

      <Section title="Stations" note={`${assets.length} periods`} />

      <Section title="Surface products (Europe-wide)" note={`${products.length} periods`} />
    </>
  );
}

function Results({ context }: { readonly context: ExplorerContext }) {
  const { manifest, navigate } = context;
  const runs = manifest.results.runs_not_persisted.map((run) => (
    <div className="torne-explorer__run" key={run.mission_id}>
      <EntityRow
        name={run.mission_id}
        code
        onOpen={() => navigate(`/mission/${run.mission_id}`)}
        status={run.status}
        rank={manifest.statuses.find((s) => s.status === run.status)?.rank ?? 0}
      />
      <FactList facts={run.produced} />
    </div>
  ));

  return (
    <>
      <Breadcrumbs items={[{ label: 'Europe', href: '/' }, { label: 'Published results' }]} />
      <PageHeader
        eyebrow="RESULTS"
        title="Published results"
        lede="The results the repository has persisted, and the runs that produced a product without persisting it."
      />

      <Section title="Persisted results">
        <ResultsSummary context={context} />
      </Section>

      <Section title="Produced in a run, not persisted">
        {runs.length === 0 ? <p className="torne-explorer__muted">None.</p> : runs}
      </Section>
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
