/**
 * The confrontation.
 *
 * The product was confronted with an independent source, and the confrontation
 * is what makes the product usable rather than merely produced. The figures
 * are the product's own, and the day-by-day rows are shown in full: a reader
 * who doubts the median can read the median's rows.
 */
import { useMemo } from 'react';

import { DataTable } from '@/components/data/DataTable';
import { LoadingState } from '@/components/ui/LoadingState';
import { formatRelative, formatValue } from '@/features/supply/mapping';
import { useProductConfrontation } from '@/features/supply/resources';
import { Section } from '@/features/supply/views/Reading';
import type { ApiProductDetail } from '@/types/api/manifest';

/** One row of the confrontation: a day, and what the two sources said. */
interface ConfrontationRow {
  readonly key: string;
  readonly operatorTerminal: string;
  readonly terminalEic: string;
  readonly alsiDay: string;
  readonly operatorDay: string;
  readonly alsiStock: number | null;
  readonly operatorStock: number | null;
  readonly absoluteDifference: number | null;
  readonly relativeDifference: number | null;
}

export interface ConfrontationSectionProps {
  readonly product: ApiProductDetail;
}

export function ConfrontationSection({ product }: ConfrontationSectionProps) {
  const { data, error, loading } = useProductConfrontation(product.product_id);
  const validation = product.validation;

  const rows = useMemo<readonly ConfrontationRow[]>(
    () =>
      (data?.rows ?? []).map((row) => ({
        key: `${row.terminal_eic}-${row.alsi_day}`,
        operatorTerminal: row.operator_terminal,
        terminalEic: row.terminal_eic,
        alsiDay: row.alsi_day,
        operatorDay: row.operator_day,
        alsiStock: row.alsi_stock_gwh ?? null,
        operatorStock: row.operator_stock_gwh ?? null,
        absoluteDifference: row.absolute_difference_gwh ?? null,
        relativeDifference: row.relative_difference ?? null,
      })),
    [data],
  );

  return (
    <Section
      title="The confrontation"
      note={`${validation.comparisons} comparisons`}
    >
      <dl className="torne-supply__facts">
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">Comparisons</dt>
          <dd className="torne-supply__fact-value">{formatValue(validation.comparisons)}</dd>
        </div>
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">Median relative difference</dt>
          <dd className="torne-supply__fact-value">
            {formatRelative(validation.median_relative_difference)}
          </dd>
        </div>
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">Maximum relative difference</dt>
          <dd className="torne-supply__fact-value">
            {formatRelative(validation.max_relative_difference)}
          </dd>
        </div>
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">Median relative difference, network flow</dt>
          <dd className="torne-supply__fact-value">
            {formatRelative(validation.median_relative_difference_network_flow)}
          </dd>
        </div>
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">Median relative difference, volumes</dt>
          <dd className="torne-supply__fact-value">
            {formatRelative(validation.median_relative_difference_volume)}
          </dd>
        </div>
        {validation.aligned_days !== null ? (
          <div className="torne-supply__fact">
            <dt className="torne-supply__fact-name">Aligned days</dt>
            <dd className="torne-supply__fact-value">{validation.aligned_days}</dd>
          </div>
        ) : null}
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">Method</dt>
          <dd className="torne-supply__fact-value">{validation.method}</dd>
        </div>
        {validation.residual !== null ? (
          <div className="torne-supply__fact">
            <dt className="torne-supply__fact-name">Residual</dt>
            <dd className="torne-supply__fact-value">{validation.residual}</dd>
          </div>
        ) : null}
      </dl>

      {loading ? <LoadingState label="Reading the confrontation…" /> : null}
      {error !== null ? (
        <p className="torne-supply__failure" role="status">
          {error}
        </p>
      ) : null}

      {rows.length > 0 ? (
        <div className="torne-supply__scroll">
          <DataTable<ConfrontationRow>
            caption="The day-by-day comparisons with the independent source"
            columns={[
              { key: 'operatorTerminal', header: 'Operator terminal', width: '11rem' },
              { key: 'terminalEic', header: 'Terminal', width: '11rem' },
              { key: 'alsiDay', header: 'Platform day', width: '9rem' },
              { key: 'operatorDay', header: 'Operator day', width: '9rem' },
              {
                key: 'alsiStock',
                header: 'Platform stock (GWh)',
                align: 'end',
                render: (row) => formatValue(row.alsiStock),
              },
              {
                key: 'operatorStock',
                header: 'Operator stock (GWh)',
                align: 'end',
                render: (row) => formatValue(row.operatorStock),
              },
              {
                key: 'absoluteDifference',
                header: 'Absolute difference (GWh)',
                align: 'end',
                render: (row) => formatValue(row.absoluteDifference),
              },
              {
                key: 'relativeDifference',
                header: 'Relative difference',
                align: 'end',
                render: (row) => formatRelative(row.relativeDifference),
              },
            ]}
            rows={rows}
            getRowKey={(row) => row.key}
          />
        </div>
      ) : null}
    </Section>
  );
}
