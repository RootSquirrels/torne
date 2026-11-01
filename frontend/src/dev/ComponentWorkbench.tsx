/**
 * The component workbench.
 *
 * An internal page that shows the design system and the scientific charts on
 * their own, so they can be tested and evolved independently of the
 * missions.
 *
 * Everything it displays is **synthetic demo data**. It never reaches the
 * scientific catalogue, the manifest, or a published result: the manifest is
 * built by the Python package from the repository's own evidence, and
 * nothing there reads this page.
 */
import { lazy, Suspense, useState } from 'react';
import type { ReactNode } from 'react';

import { Badge } from '@/components/ui/Badge';
import { Breadcrumbs } from '@/components/ui/Breadcrumbs';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DataTable } from '@/components/data/DataTable';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { FilterBar } from '@/components/ui/FilterBar';
import { IconButton } from '@/components/ui/IconButton';
import { Input } from '@/components/ui/Input';
import { Legend } from '@/components/ui/Legend';
import { LoadingState } from '@/components/ui/LoadingState';
import { SpatialMap } from '@/components/visualization/SpatialMap';
import { MetricCard } from '@/components/data/MetricCard';
import { Panel } from '@/components/ui/Panel';
import { ProvenanceLink } from '@/components/ui/ProvenanceLink';
import { Select } from '@/components/ui/Select';
import { StatusIndicator } from '@/components/ui/StatusIndicator';
import { Tabs } from '@/components/ui/Tabs';
import { Tooltip } from '@/components/ui/Tooltip';
import {
  DEMO_NOTICE,
  demoCoveragePeriods,
  demoSeriesWithoutInterval,
  demoSpatialScene,
  demoTimeSeries,
  demoVerticalProfiles,
} from '@/features/workbench/demoData';
import type { ApiRef } from '@/types/api/manifest';
import './ComponentWorkbench.css';

interface DemoRow {
  readonly id: string;
  readonly station: string;
  readonly value: number | null;
  readonly state: string;
  readonly quality: string;
}

const DEMO_ROWS: readonly DemoRow[] = [
  { id: 'demo-1', station: 'Demo station Alpha', value: 412, state: 'measured', quality: 'declared' },
  { id: 'demo-2', station: 'Demo station Alpha', value: null, state: 'absent', quality: 'unknown' },
  { id: 'demo-3', station: 'Demo station Beta', value: 2.19, state: 'estimated', quality: 'source_estimated' },
  { id: 'demo-4', station: 'Demo station Gamma', value: 0, state: 'measured', quality: 'declared' },
];

const DEMO_REFERENCE: ApiRef = {
  kind: 'document',
  target: 'docs/ARCHITECTURE.md §5',
  url: 'https://github.com/RootSquirrels/torne/blob/main/docs/ARCHITECTURE.md',
};

/**
 * The charts are loaded on demand.
 *
 * The workbench is the page that shows every chart, so it is the page that
 * pays for the chart library — but only once it is opened. The rest of the
 * application never downloads it.
 */
const CoverageTimeline = lazy(() =>
  import('@/components/visualization/CoverageTimeline').then((module) => ({
    default: module.CoverageTimeline,
  })),
);
const TimeSeriesChart = lazy(() =>
  import('@/components/visualization/TimeSeriesChart').then((module) => ({
    default: module.TimeSeriesChart,
  })),
);
const UncertaintyChart = lazy(() =>
  import('@/components/visualization/UncertaintyChart').then((module) => ({
    default: module.UncertaintyChart,
  })),
);
const VerticalProfileChart = lazy(() =>
  import('@/components/visualization/VerticalProfileChart').then((module) => ({
    default: module.VerticalProfileChart,
  })),
);

interface LazyProps {
  readonly children: ReactNode;
}

/** The boundary the lazily loaded charts are drawn inside. */
function Lazy({ children }: LazyProps) {
  return <Suspense fallback={<LoadingState label="Loading the component…" />}>{children}</Suspense>;
}

export function ComponentWorkbench() {
  const [tab, setTab] = useState('states');
  const [domain, setDomain] = useState('');
  const [text, setText] = useState('');

  return (
    <div className="torne-workbench">
      <div className="torne-workbench__notice" role="note">
        <strong>Synthetic demo data.</strong> Every value on this page was invented for the
        workbench. It measures nothing, it comes from no source, and it establishes nothing. This
        page never feeds the catalogue, the manifest, or a published result.
      </div>

      <h1 className="torne-workbench__title">Component workbench</h1>

      <Tabs
        ariaLabel="Workbench sections"
        activeId={tab}
        onChange={setTab}
        tabs={[
          { id: 'states', label: 'UI components' },
          { id: 'charts', label: 'Scientific charts' },
          { id: 'data', label: 'Data display' },
        ]}
      >
        {tab === 'states' ? (
        <div className="torne-workbench__section">
          <Panel title="Buttons" description="Every variant, every state.">
            <div className="torne-workbench__row">
              <Button variant="primary">Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button variant="primary" loading>
                Loading
              </Button>
              <Button variant="secondary" disabled>
                Disabled
              </Button>
            </div>
            <div className="torne-workbench__row">
              <IconButton
                icon={<span aria-hidden="true">↺</span>}
                label="Reset the filters"
                onClick={() => undefined}
              />
              <Tooltip content="A tooltip opens on hover and on focus.">
                <Button variant="secondary">Hover me</Button>
              </Tooltip>
            </div>
          </Panel>

          <Panel title="Inputs" description="A label, a value, and the states that qualify it.">
            <div className="torne-workbench__row">
              <Input label="Station" value={text} onChange={setText} placeholder="Demo station" />
              <Input
                label="With an error"
                value=""
                onChange={() => undefined}
                error="This value does not satisfy the contract."
              />
              <Input
                label="With a hint"
                value=""
                onChange={() => undefined}
                hint="The name the source gives the station."
              />
              <Select
                label="Domain"
                value={domain}
                onChange={setDomain}
                options={[
                  { value: '', label: 'All domains' },
                  { value: 'hydrology', label: 'Hydrology' },
                  { value: 'atmosphere', label: 'Atmosphere' },
                ]}
              />
            </div>
          </Panel>

          <Panel title="Status" description="The ordinal science ramp, and the semantic register.">
            <div className="torne-workbench__row">
              {(['not covered', 'qualification', 'exploration', 'demonstration', 'knowledge'] as const).map(
                (status, rank) => (
                  <StatusIndicator key={status} status={status} rank={rank} />
                ),
              )}
            </div>
            <div className="torne-workbench__row">
              <Badge tone="neutral">neutral</Badge>
              <Badge tone="info">info</Badge>
              <Badge tone="success">success</Badge>
              <Badge tone="warning">warning</Badge>
              <Badge tone="danger">danger</Badge>
            </div>
            <div className="torne-workbench__row">
              <ProvenanceLink reference={DEMO_REFERENCE} />
            </div>
          </Panel>

          <Panel title="Breadcrumbs and filters" description="Navigation and narrowing.">
            <Breadcrumbs
              items={[
                { label: 'Europe', href: '/' },
                { label: 'France', href: '/country/FR' },
                { label: 'Hydrology' },
              ]}
            />
            <FilterBar onReset={() => setDomain('')}>
              <Select
                label="Domain"
                value={domain}
                onChange={setDomain}
                options={[
                  { value: '', label: 'All domains' },
                  { value: 'hydrology', label: 'Hydrology' },
                ]}
              />
            </FilterBar>
          </Panel>

          <Panel title="States" description="Loading, empty and failed.">
            <div className="torne-workbench__row">
              <LoadingState label="Loading the synthetic series…" />
            </div>
            <div className="torne-workbench__row">
              <EmptyState
                title="Nothing to show"
                description="The demo data has no series in this range."
              />
            </div>
            <div className="torne-workbench__row">
              <ErrorState message="The synthetic source did not answer." onRetry={() => undefined} />
            </div>
          </Panel>
        </div>
      ) : null}

      {tab === 'charts' ? (
        <div className="torne-workbench__section">
          <Panel
            title="Time series"
            description="Two series of different frequencies, with gaps, an interval, and a forecast that starts mid-way."
          >
            <Lazy>
              <TimeSeriesChart
              title="Discharge and water level"
              description={DEMO_NOTICE}
              series={demoTimeSeries}
              unit="m³/s"
              height={300}
              />
            </Lazy>
          </Panel>

          <Panel
            title="A series without uncertainty"
            description="No interval is provided, so no band is drawn."
          >
            <Lazy>
              <TimeSeriesChart
              title="Stage, with no interval"
              description={DEMO_NOTICE}
              series={demoSeriesWithoutInterval}
              height={220}
              />
            </Lazy>
          </Panel>

          <Panel title="Uncertainty" description="Central interval, quantiles and envelopes.">
            <Lazy>
              <UncertaintyChart
              title="Discharge with its interval"
              description={DEMO_NOTICE}
              series={demoTimeSeries}
              unit="m³/s"
              height={280}
              />
            </Lazy>
          </Panel>

          <Panel
            title="Vertical profile"
            description="Irregular pressure levels, a missing value, and a flagged level."
          >
            <Lazy>
              <VerticalProfileChart
              title="Two synthetic casts"
              description={DEMO_NOTICE}
              profiles={demoVerticalProfiles}
              variableKey="temperature"
              height={320}
              />
            </Lazy>
          </Panel>

          <Panel title="Coverage" description="Observed, published and revised periods, and the gaps between them.">
            <Lazy>
              <CoverageTimeline
              title="Synthetic coverage"
              description={DEMO_NOTICE}
              periods={demoCoveragePeriods}
              height={260}
              />
            </Lazy>
          </Panel>

          <Panel title="Map" description="Points, a zone and a grid.">
            <Lazy>
              <SpatialMap
              scene={demoSpatialScene}
              title="A synthetic scene"
              description={DEMO_NOTICE}
              height={320}
              legend={
                <Legend
                  title="What the colours mean"
                  items={[
                    { label: 'demo station', color: 'var(--map-marker)', shape: 'circle' },
                    { label: 'demo basin', color: 'var(--series-3)', shape: 'square' },
                  ]}
                />
              }
              />
            </Lazy>
          </Panel>
        </div>
      ) : null}

      {tab === 'data' ? (
        <div className="torne-workbench__section">
          <Panel title="Metrics" description="A number, its unit, and the evidence behind it.">
            <div className="torne-workbench__grid">
              <MetricCard
                label="Demo discharge"
                value="412"
                unit="m³/s"
                hint="Synthetic value."
                provenance={[DEMO_REFERENCE]}
              />
              <MetricCard
                label="Demo change"
                value="+3.1"
                unit="%"
                delta={{ value: '+3.1 %', direction: 'up', label: 'against the previous day' }}
              />
              <MetricCard label="Demo absent value" value="—" hint="A missing measurement stays missing." />
            </div>
          </Panel>

          <Panel title="Table" description="Rows, and what an absent value looks like.">
            <DataTable
              caption="Synthetic demo rows"
              rows={DEMO_ROWS}
              getRowKey={(row) => row.id}
              columns={[
                { key: 'station', header: 'Station' },
                {
                  key: 'value',
                  header: 'Value',
                  align: 'end',
                  render: (row) => (row.value === null ? 'no value' : String(row.value)),
                },
                { key: 'state', header: 'State' },
                { key: 'quality', header: 'Quality' },
              ]}
            />
          </Panel>

          <Panel title="Cards" description="Surfaces that group what belongs together.">
            <Card title="Demo card" subtitle="A grouped set of facts">
              <p>Everything here is synthetic.</p>
            </Card>
          </Panel>
        </div>
      ) : null}
      </Tabs>
    </div>
  );
}
