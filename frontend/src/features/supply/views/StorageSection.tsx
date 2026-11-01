/**
 * The storage layer.
 *
 * The layer publishes a state for some of the countries it covers, and
 * declares the ones it did not. Both are shown: the states that were
 * published, and the absences that were declared. An absence is never hidden
 * and never shown as a zero.
 */
import { useMemo } from 'react';

import { DataTable } from '@/components/data/DataTable';
import { LoadingState } from '@/components/ui/LoadingState';
import { declaredAbsences, declaredCoverage, formatValue, readStates } from '@/features/supply/mapping';
import type { SupplyLayer, SupplyState } from '@/features/supply/mapping';
import { useProductStates } from '@/features/supply/resources';
import { DeclaredAbsences } from '@/features/supply/views/DeclaredAbsences';
import { Section } from '@/features/supply/views/Reading';
import type { ApiProductDetail } from '@/types/api/manifest';

/** One row of the table of published states. */
interface StorageRow {
  readonly entity: string;
  readonly day: string;
  readonly values: Readonly<Record<string, number | null>>;
}

export interface StorageSectionProps {
  readonly product: ApiProductDetail;
  readonly layer: SupplyLayer;
}

export function StorageSection({ product, layer }: StorageSectionProps) {
  const { data, error, loading } = useProductStates(product.product_id, layer.id, undefined);
  const states = useMemo(() => readStates(data?.states ?? []), [data]);

  const coverage = declaredCoverage(product, layer.id);
  const absences = declaredAbsences(product, layer.id);

  const rows = useMemo<readonly StorageRow[]>(
    () =>
      states.map((state: SupplyState) => ({
        entity: state.entity,
        day: state.day,
        values: state.values,
      })),
    [states],
  );

  return (
    <Section
      title={layer.title}
      note={
        coverage.length === 0
          ? undefined
          : `${states.length} of the ${coverage.length} countries the platform answered for published a state · ${absences.length} published none`
      }
    >
      {loading ? <LoadingState label="Reading the storage states…" /> : null}
      {error !== null ? (
        <p className="torne-supply__failure" role="status">
          {error}
        </p>
      ) : null}

      {rows.length > 0 ? (
        <div className="torne-supply__scroll">
          <DataTable<StorageRow>
            caption={`The published states of the ${layer.title} layer`}
            columns={[
              { key: 'entity', header: layer.entityColumn, width: '7rem' },
              { key: 'day', header: layer.dayColumn, width: '9rem' },
              ...layer.measures.map((measure) => ({
                key: measure.column,
                header: measure.unit === null ? measure.label : `${measure.label} (${measure.unit})`,
                align: 'end' as const,
                render: (row: StorageRow) => formatValue(row.values[measure.column] ?? null),
              })),
            ]}
            rows={rows}
            getRowKey={(row) => row.entity}
          />
        </div>
      ) : null}

      <DeclaredAbsences product={product} layer={layer} />
    </Section>
  );
}
