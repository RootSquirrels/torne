/**
 * The terminals, on a map.
 *
 * The map is one channel and never the only one: the entities it draws are
 * also listed beside it, with the measures the product published for them,
 * and the flag the map colours them by is written in words in the same
 * table. A reader who cannot use colour reads the table; a reader who
 * cannot use the map reads it too.
 *
 * The map library is loaded on demand.
 */
import { Suspense, lazy, useMemo, useState } from 'react';

import { DataTable } from '@/components/data/DataTable';
import { LoadingState } from '@/components/ui/LoadingState';
import { Legend } from '@/components/ui/Legend';
import type { LegendItem } from '@/components/ui/Legend';
import { useChartTokens } from '@/components/visualization/chartTheme';
import { formatValue, NOT_ESTABLISHED, readStates } from '@/features/supply/mapping';
import type { SupplyLayer, SupplyState } from '@/features/supply/mapping';
import { useProductStates } from '@/features/supply/resources';
import { DeclaredAbsences } from '@/features/supply/views/DeclaredAbsences';
import { FlagBadge } from '@/features/supply/views/FlagBadge';
import { Section } from '@/features/supply/views/Reading';
import { TerminalSeries } from '@/features/supply/views/TerminalSeries';
import type { ApiProductDetail } from '@/types/api/manifest';
import type { SpatialPoint, SpatialScene } from '@/types/visualization/spatial';

const LazySpatialMap = lazy(() =>
  import('@/components/visualization/SpatialMap').then((module) => ({
    default: module.SpatialMap,
  })),
);

/** A state that carries a position. */
interface PositionedState extends SupplyState {
  readonly latitude: number;
  readonly longitude: number;
}

function isPositioned(state: SupplyState): state is PositionedState {
  return state.latitude !== null && state.longitude !== null;
}

/** One row of the table of installations. */
interface InstallationRow {
  readonly entity: string;
  readonly label: string;
  readonly country: string;
  readonly values: Readonly<Record<string, number | null>>;
  readonly flags: Readonly<Record<string, boolean | null>>;
}

export interface TerminalsSectionProps {
  readonly product: ApiProductDetail;
  readonly layer: SupplyLayer;
}

export function TerminalsSection({ product, layer }: TerminalsSectionProps) {
  const { data, error, loading } = useProductStates(product.product_id, layer.id, undefined);
  const states = useMemo(() => readStates(data?.states ?? []), [data]);
  const tokens = useChartTokens();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // The flag the map is coloured by: the layer's own first flag. A layer that
  // publishes no flag colours nothing, and says so.
  const flag = layer.flags[0] ?? null;

  const fillOf = useMemo(
    () =>
      (state: SupplyState): string | null => {
        if (flag === null) {
          return null;
        }
        const value = state.flags[flag.column] ?? null;
        if (value === null) {
          // The product said nothing about the flag: no colour is invented.
          return null;
        }
        return value ? tokens.warning : tokens.mapMarker;
      },
    [flag, tokens],
  );

  const positioned = useMemo(() => states.filter(isPositioned), [states]);

  const scene = useMemo<SpatialScene>(() => {
    const points: SpatialPoint[] = positioned.map((state) => {
      const properties: Record<string, string | number | boolean | null> = {
        Country: state.country,
        [layer.dayColumn]: state.day,
      };
      for (const measure of layer.measures) {
        const value = state.values[measure.column] ?? null;
        properties[measure.label] =
          value === null
            ? NOT_ESTABLISHED
            : measure.unit === null
              ? formatValue(value)
              : `${formatValue(value)} ${measure.unit}`;
      }
      for (const entry of layer.flags) {
        const value = state.flags[entry.column] ?? null;
        properties[entry.label] =
          value === null ? NOT_ESTABLISHED : value ? 'yes' : 'no';
      }
      return {
        id: state.entity,
        label: state.label,
        position: [state.longitude, state.latitude],
        kind: layer.title,
        layerId: layer.id,
        fill: fillOf(state),
        properties,
      };
    });

    return {
      layers: [
        { id: layer.id, label: layer.title, visible: true, kind: 'point', description: null },
      ],
      points,
      areas: [],
      grids: [],
      provenance: [],
    };
  }, [positioned, layer, fillOf]);

  const bounds = useMemo(() => {
    if (positioned.length === 0) {
      return undefined;
    }
    const longitudes = positioned.map((state) => state.longitude);
    const latitudes = positioned.map((state) => state.latitude);
    return [
      [Math.min(...latitudes), Math.min(...longitudes)],
      [Math.max(...latitudes), Math.max(...longitudes)],
    ] as const;
  }, [positioned]);

  const legendItems = useMemo<readonly LegendItem[]>(() => {
    if (flag === null) {
      return [];
    }
    return [
      {
        label: flag.label,
        color: tokens.warning,
        shape: 'circle',
        description: 'the product sets this flag',
      },
      {
        label: `Not ${flag.label.toLowerCase()}`,
        color: tokens.mapMarker,
        shape: 'circle',
        description: 'the product does not set this flag',
      },
    ];
  }, [flag, tokens]);

  const rows = useMemo<readonly InstallationRow[]>(
    () =>
      states.map((state) => ({
        entity: state.entity,
        label: state.label,
        country: state.country,
        values: state.values,
        flags: state.flags,
      })),
    [states],
  );

  const selected = states.find((state) => state.entity === selectedId) ?? null;
  const unflagged = flag === null ? 0 : states.filter((state) => state.flags[flag.column] === null).length;

  return (
    <Section
      title={layer.title}
      note={
        states.length === 0
          ? undefined
          : `${states.length} installations · ${layer.window.start ?? '?'} → ${layer.window.end ?? '?'}`
      }
    >
      {loading ? <LoadingState label="Reading the installations…" /> : null}
      {error !== null ? (
        <p className="torne-supply__failure" role="status">
          {error}
        </p>
      ) : null}

      {states.length > 0 ? (
        <div className="torne-supply__split">
          <div className="torne-supply__map">
            <Suspense fallback={<LoadingState label="Loading the map…" />}>
              <LazySpatialMap
                scene={scene}
                title={layer.title}
                description={layer.file === null ? null : layer.file}
                height={420}
                selectedId={selectedId}
                onSelect={(selection) => setSelectedId(selection?.id ?? null)}
                onNavigate={(selection) => setSelectedId(selection.id)}
                {...(bounds === undefined ? {} : { bounds })}
                legend={
                  flag === null ? (
                    <p className="torne-supply__note">
                      The layer publishes no flag: the markers carry no value and are drawn in the
                      neutral colour.
                    </p>
                  ) : (
                    <Legend title={flag.label} items={legendItems} orientation="column" />
                  )
                }
              />
            </Suspense>
            {positioned.length < states.length ? (
              <p className="torne-supply__note">
                {states.length - positioned.length} installations have no established position and
                are not drawn on the map; they are in the table below.
              </p>
            ) : null}
            {unflagged > 0 ? (
              <p className="torne-supply__note">
                {unflagged} installations have no established value for “{flag?.label ?? ''}”.
              </p>
            ) : null}
          </div>

          <div className="torne-supply__table">
            <DataTable<InstallationRow>
              caption={`The installations of the ${layer.title} layer`}
              columns={[
                {
                  key: 'label',
                  header: layer.labelColumn,
                  render: (row) => (
                    <span className="torne-supply__entity">
                      <span className="torne-supply__entity-name">{row.label}</span>
                      <span className="torne-supply__entity-id">{row.entity}</span>
                    </span>
                  ),
                },
                { key: 'country', header: layer.countryColumn, width: '5rem' },
                ...layer.measures.map((measure) => ({
                  key: measure.column,
                  header: measure.unit === null ? measure.label : `${measure.label} (${measure.unit})`,
                  align: 'end' as const,
                  render: (row: InstallationRow) => formatValue(row.values[measure.column] ?? null),
                })),
                ...layer.flags.map((entry) => ({
                  key: entry.column,
                  header: entry.label,
                  render: (row: InstallationRow) => (
                    <FlagBadge label={entry.label} value={row.flags[entry.column] ?? null} />
                  ),
                })),
              ]}
              rows={rows}
              getRowKey={(row) => row.entity}
              onRowClick={(row) => setSelectedId(row.entity)}
            />
          </div>
        </div>
      ) : null}

      {selected !== null ? (
        <TerminalSeries
          productId={product.product_id}
          layer={layer}
          entity={selected.entity}
          title={selected.label}
        />
      ) : null}

      <DeclaredAbsences product={product} layer={layer} />
    </Section>
  );
}
