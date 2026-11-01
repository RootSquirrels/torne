/**
 * The series of one installation.
 *
 * The chart is drawn from the states the API serves for that entity: the
 * whole series, day by day. A day the product did not establish keeps its
 * hole — the line breaks there, and the table writes the absence instead of a
 * zero.
 *
 * The chart library is loaded on demand: a reader who never opens the supply
 * branch does not download it.
 */
import { Suspense, lazy, useMemo, useState } from 'react';

import { DataTable } from '@/components/data/DataTable';
import { LoadingState } from '@/components/ui/LoadingState';
import { Select } from '@/components/ui/Select';
import { formatValue, readStates, toSeries } from '@/features/supply/mapping';
import type { SupplyLayer } from '@/features/supply/mapping';
import { useProductStates } from '@/features/supply/resources';
import { Section } from '@/features/supply/views/Reading';

const LazyTimeSeriesChart = lazy(() =>
  import('@/components/visualization/TimeSeriesChart').then((module) => ({
    default: module.TimeSeriesChart,
  })),
);

/** One row of the series: a day, and what the product published for it. */
interface SeriesRow {
  readonly day: string;
  readonly values: Readonly<Record<string, number | null>>;
}

export interface TerminalSeriesProps {
  readonly productId: string;
  readonly layer: SupplyLayer;
  readonly entity: string;
  /** The name of the installation, as the product writes it. */
  readonly title: string;
}

export function TerminalSeries({ productId, layer, entity, title }: TerminalSeriesProps) {
  const { data, error, loading } = useProductStates(productId, layer.id, entity);
  const states = useMemo(() => readStates(data?.states ?? []), [data]);

  const [column, setColumn] = useState<string>(layer.measures[0]?.column ?? '');
  const measure = layer.measures.find((entry) => entry.column === column) ?? layer.measures[0] ?? null;

  const series = useMemo(
    () => (measure === null ? null : toSeries(states, measure, entity)),
    [states, measure, entity],
  );

  const rows = useMemo<readonly SeriesRow[]>(
    () => states.map((state) => ({ day: state.day, values: state.values })),
    [states],
  );

  const absent = useMemo(
    () => (measure === null ? 0 : states.filter((state) => state.values[measure.column] === null).length),
    [states, measure],
  );

  return (
    <Section
      title={`The series of ${title}`}
      note={states.length === 0 ? undefined : `${states.length} days`}
    >
      {layer.measures.length > 1 && measure !== null ? (
        <Select
          label="Measure"
          value={measure.column}
          options={layer.measures.map((entry) => ({
            value: entry.column,
            label: entry.unit === null ? entry.label : `${entry.label} (${entry.unit})`,
          }))}
          onChange={setColumn}
          hint={`${absent} of the ${states.length} days have no value for this measure.`}
        />
      ) : null}

      {loading ? <LoadingState label="Reading the series…" /> : null}
      {error !== null ? <p className="torne-supply__failure" role="status">{error}</p> : null}

      {series !== null && states.length > 0 ? (
        <Suspense fallback={<LoadingState label="Loading the chart…" />}>
          <LazyTimeSeriesChart
            series={[series]}
            title={measure?.label ?? entity}
            description={`${title} · ${entity}`}
            unit={measure?.unit ?? null}
            height={320}
          />
        </Suspense>
      ) : null}

      {rows.length > 0 ? (
        <div className="torne-supply__scroll">
          <DataTable<SeriesRow>
            caption={`The daily states of ${title}`}
            columns={[
              { key: 'day', header: layer.dayColumn, width: '9rem' },
              ...layer.measures.map((entry) => ({
                key: entry.column,
                header: entry.unit === null ? entry.label : `${entry.label} (${entry.unit})`,
                align: 'end' as const,
                render: (row: SeriesRow) => formatValue(row.values[entry.column] ?? null),
              })),
            ]}
            rows={rows}
            getRowKey={(row) => row.day}
          />
        </div>
      ) : null}
    </Section>
  );
}
