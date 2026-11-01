/**
 * The spatial map.
 *
 * Leaflet is kept: it answers the need, and the mission explicitly forbids a
 * migration to another engine or to a 3D globe. What changes is that the map
 * becomes a **component with a contract** rather than a script that happens
 * to draw the catalogue.
 *
 * Two deliberate choices:
 *
 * - **No tile server.** The map shows TORNE's own layers on a plain
 *   background. An external tile service would make the application depend
 *   on a third party at runtime, and would draw a world the explorer knows
 *   nothing about.
 * - **No image markers.** Points are drawn as SVG circle markers, so nothing
 *   depends on a bundler-friendly icon path.
 *
 * The map is not the only way to read it: the component also renders the
 * layers as a list, and every entity can be reached from there.
 *
 * **Two actions, two ways.** Clicking a shape *selects* it; opening it is a
 * separate act. On the map, opening is a double click — a mouse gesture. In
 * the entity list, which is the keyboard-reachable equivalent of the map,
 * opening is a **single activation**: a double click cannot be performed from
 * a keyboard, so a list whose only way to open an entity were a double click
 * would be unreachable for the readers who use one.
 */
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import './SpatialMap.css';
import { useChartTokens } from '@/components/visualization/chartTheme';
import { escapeHtml } from '@/components/visualization/html';
import type {
  SpatialArea,
  SpatialLayer,
  SpatialPoint,
  SpatialScene,
  SpatialSelection,
} from '@/types/visualization/spatial';

export interface SpatialMapProps {
  /** What the map draws. */
  readonly scene: SpatialScene;
  readonly title: string;
  readonly description?: string | null;
  readonly height?: number;
  /** The entity being read, by its identifier. The entity list marks it. */
  readonly selectedId?: string | null;
  /** Called when an entity is selected, and with `null` when the selection is cleared. */
  readonly onSelect?: (selection: SpatialSelection | null) => void;
  /**
   * Called when the reader asks to open an entity.
   *
   * The entity list opens on a single activation; the map opens on a double
   * click, because a shape is not focusable.
   */
  readonly onNavigate?: (selection: SpatialSelection) => void;
  /** The extent to fit, as [[south, west], [north, east]]. */
  readonly bounds?: readonly (readonly [number, number])[];
  /** The initial centre, as [latitude, longitude]. */
  readonly centre?: readonly [number, number];
  /** The initial zoom. */
  readonly zoom?: number;
  /**
   * A control that returns the view to a known extent.
   *
   * While the reader has not moved the map, the view follows the container:
   * a resize re-fits the extent, because a fit on a narrow container would
   * otherwise leave everything out of sight. Any interaction hands the view
   * over to the reader, and the control takes it back.
   */
  readonly fitTo?: {
    readonly label: string;
    readonly bounds: readonly (readonly [number, number])[];
  };
  /** The legend, drawn beside the map. */
  readonly legend?: ReactNode;
}

interface Style {
  readonly fill: string;
  readonly stroke: string;
  readonly ink: string;
  readonly marker: string;
  readonly selected: string;
}

function propertiesToLines(properties: Readonly<Record<string, string | number | boolean | null>>): string {
  const entries = Object.entries(properties).filter(([, value]) => value !== null);
  if (entries.length === 0) {
    return '';
  }
  return entries
    .map(
      ([key, value]) =>
        `<div><strong>${escapeHtml(key)}</strong>: ${escapeHtml(String(value))}</div>`,
    )
    .join('');
}

export function SpatialMap({
  scene,
  title,
  description = null,
  height = 420,
  selectedId = null,
  onSelect,
  onNavigate,
  bounds,
  centre,
  zoom = 4,
  fitTo,
  legend,
}: SpatialMapProps) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<L.Map | null>(null);
  const groups = useRef<Map<string, L.LayerGroup>>(new Map());
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());
  const [followsExtent, setFollowsExtent] = useState(true);
  const [failure, setFailure] = useState<string | null>(null);
  const tokens = useChartTokens();

  const style = useMemo<Style>(
    () => ({
      fill: tokens.mapLand,
      stroke: tokens.mapBoundary,
      ink: tokens.text,
      marker: tokens.mapMarker,
      selected: tokens.mapMarkerSelected,
    }),
    [tokens],
  );

  useEffect(() => {
    const element = container.current;
    if (element === null) {
      return;
    }
    let instance: L.Map;
    try {
      instance = L.map(element, {
        zoomControl: true,
        attributionControl: false,
        worldCopyJump: true,
        zoomSnap: 0.25,
        minZoom: 2,
      });
    } catch (error) {
      // Reporting an initialisation failure is not a cascading render: it
      // happens once, and only when the canvas could not be created at all.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFailure(error instanceof Error ? error.message : 'the map could not be created');
      return;
    }
    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (instance === null) {
      return;
    }

    for (const group of groups.current.values()) {
      group.clearLayers();
    }
    groups.current.clear();

    for (const layer of scene.layers) {
      const group = L.layerGroup();
      groups.current.set(layer.id, group);

      for (const point of scene.points.filter((entry) => entry.layerId === layer.id)) {
        const marker = L.circleMarker([point.position[1], point.position[0]], {
          radius: 6,
          color: style.ink,
          weight: 1,
          fillColor: style.marker,
          fillOpacity: 1,
        });
        marker.bindTooltip(`${escapeHtml(point.label)} · ${escapeHtml(point.kind)}`, {
          direction: 'top',
        });
        marker.bindPopup(
          `<strong>${escapeHtml(point.label)}</strong><div>${escapeHtml(point.kind)}</div>${propertiesToLines(point.properties)}`,
        );
        marker.on('click', () => onSelect?.({ kind: 'point', id: point.id }));
        marker.on('dblclick', () => onNavigate?.({ kind: 'point', id: point.id }));
        group.addLayer(marker);
      }

      for (const area of scene.areas.filter((entry) => entry.layerId === layer.id)) {
        const rings = area.rings.map((ring) => ring.map(([lon, lat]) => [lat, lon] as [number, number]));
        const polygon = L.polygon(rings, {
          color: style.stroke,
          weight: 1,
          fillColor: area.fill ?? style.fill,
          fillOpacity: area.fillOpacity ?? (area.fill === null ? 0.6 : 1),
        });
        polygon.bindTooltip(escapeHtml(area.label), { sticky: true });
        polygon.bindPopup(
          `<strong>${escapeHtml(area.label)}</strong>${propertiesToLines(area.properties)}`,
        );
        polygon.on('click', () => onSelect?.({ kind: 'area', id: area.id }));
        polygon.on('dblclick', () => onNavigate?.({ kind: 'area', id: area.id }));
        group.addLayer(polygon);
      }

      for (const grid of scene.grids.filter((entry) => entry.layerId === layer.id)) {
        const rectangle = L.rectangle(
          [
            [grid.extent.south, grid.extent.west],
            [grid.extent.north, grid.extent.east],
          ],
          { color: style.stroke, weight: 1, fill: false, dashArray: '4 3' },
        );
        rectangle.bindTooltip(`${escapeHtml(grid.label)} · ${escapeHtml(grid.crs)}`, {
          sticky: true,
        });
        rectangle.on('click', () => onSelect?.({ kind: 'grid', id: grid.id }));
        rectangle.on('dblclick', () => onNavigate?.({ kind: 'grid', id: grid.id }));
        group.addLayer(rectangle);
      }

      if (!hidden.has(layer.id)) {
        group.addTo(instance);
      }
    }
  }, [scene, style, hidden, onSelect, onNavigate]);

  const fitExtent = useCallback(
    (target: L.Map, extent: readonly (readonly [number, number])[]) => {
      const first = extent[0];
      const last = extent[extent.length - 1];
      if (first === undefined || last === undefined) {
        return;
      }
      target.fitBounds(
        [
          [first[0], first[1]],
          [last[0], last[1]],
        ],
        { animate: false },
      );
    },
    [],
  );

  /**
   * While the reader has not moved the map, the view follows the container.
   *
   * A fit on a narrow container would leave everything out of sight, and the
   * grid settles after the first fit; so a resize re-fits. Any interaction
   * hands the view over to the reader, and the control takes it back.
   */
  useEffect(() => {
    const instance = map.current;
    if (instance === null) {
      return;
    }

    const extent = fitTo?.bounds ?? bounds;
    if (extent !== undefined && extent.length >= 2) {
      fitExtent(instance, extent);
    } else if (centre !== undefined) {
      instance.setView([centre[0], centre[1]], zoom);
    }
  }, [bounds, centre, zoom, scene, fitTo, fitExtent]);

  useEffect(() => {
    const instance = map.current;
    if (instance === null) {
      return;
    }

    const handOver = () => setFollowsExtent(false);
    instance.on('dragstart', handOver);
    const container = instance.getContainer();
    container.addEventListener('wheel', handOver, { passive: true });
    container.querySelector('.leaflet-control-zoom')?.addEventListener('click', handOver);

    return () => {
      instance.off('dragstart', handOver);
      container.removeEventListener('wheel', handOver);
    };
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (instance === null || !followsExtent) {
      return;
    }
    const extent = fitTo?.bounds ?? bounds;
    if (extent === undefined) {
      return;
    }
    const remeasure = () => {
      instance.invalidateSize({ animate: false });
      fitExtent(instance, extent);
    };
    const observer = new ResizeObserver(remeasure);
    observer.observe(instance.getContainer());
    window.addEventListener('resize', remeasure);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', remeasure);
    };
  }, [followsExtent, bounds, fitTo, fitExtent]);

  const toggleLayer = (layer: SpatialLayer): void => {
    setHidden((previous) => {
      const next = new Set(previous);
      if (next.has(layer.id)) {
        next.delete(layer.id);
      } else {
        next.add(layer.id);
      }
      return next;
    });
  };

  const entities: ReadonlyArray<{ kind: 'point' | 'area' | 'grid'; id: string; label: string }> = [
    ...scene.points.map((point: SpatialPoint) => ({ kind: 'point' as const, id: point.id, label: point.label })),
    ...scene.areas.map((area: SpatialArea) => ({ kind: 'area' as const, id: area.id, label: area.label })),
    ...scene.grids.map((grid) => ({ kind: 'grid' as const, id: grid.id, label: grid.label })),
  ];

  return (
    <figure className="torne-spatial">
      <figcaption className="torne-spatial__caption">
        <span className="torne-spatial__titles">
          <span className="torne-spatial__title">{title}</span>
          {description !== null && description !== undefined ? (
            <span className="torne-spatial__description">{description}</span>
          ) : null}
        </span>
      </figcaption>

      <div className="torne-spatial__body">
        <div className="torne-spatial__canvas-wrap">
          <div
            className="torne-spatial__canvas"
            style={{ height: `${height}px` }}
            ref={container}
            role="application"
            aria-label={title}
          />
          {fitTo !== undefined ? (
            <button
              type="button"
              className="torne-spatial__fit"
              onClick={() => {
                const instance = map.current;
                if (instance === null) {
                  return;
                }
                setFollowsExtent(true);
                instance.invalidateSize({ animate: false });
                fitExtent(instance, fitTo.bounds);
              }}
            >
              {fitTo.label}
            </button>
          ) : null}
        </div>
        {failure !== null ? (
          <p className="torne-spatial__failure" role="status">
            The map could not be drawn: {failure}. The entities are listed beside it.
          </p>
        ) : null}

        <div className="torne-spatial__side">
          {legend !== undefined ? (
            <section className="torne-spatial__section" aria-label="Legend">
              {legend}
            </section>
          ) : null}
          <section className="torne-spatial__section" aria-label="Layers">
            <h3 className="torne-spatial__section-title">Layers</h3>
            {scene.layers.length === 0 ? (
              <p className="torne-spatial__empty">No layer.</p>
            ) : (
              <ul className="torne-spatial__layers">
                {scene.layers.map((layer) => (
                  <li key={layer.id}>
                    <label className="torne-spatial__layer">
                      <input
                        type="checkbox"
                        checked={!hidden.has(layer.id)}
                        onChange={() => toggleLayer(layer)}
                      />
                      <span>{layer.label}</span>
                      <span className="torne-spatial__layer-kind">{layer.kind}</span>
                    </label>
                    {layer.description !== null && layer.description !== undefined ? (
                      <p className="torne-spatial__layer-description">{layer.description}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="torne-spatial__section" aria-label="Entities">
            <h3 className="torne-spatial__section-title">Entities</h3>
            {entities.length === 0 ? (
              <p className="torne-spatial__empty">Nothing to show.</p>
            ) : (
              <ul className="torne-spatial__entities">
                {entities.map((entity) => (
                  <li key={`${entity.kind}-${entity.id}`}>
                    <button
                      type="button"
                      className="torne-spatial__entity"
                      aria-current={selectedId === entity.id ? 'page' : undefined}
                      onClick={() => onNavigate?.({ kind: entity.kind, id: entity.id })}
                    >
                      {entity.label}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </figure>
  );
}
