/**
 * The ECharts wrapper.
 *
 * ECharts is imported piecemeal — `echarts/core` plus the charts and
 * components actually used — so a page that shows no chart does not pay for
 * the chart library. The bundle is split accordingly in `vite.config.ts`.
 *
 * The wrapper owns the lifecycle: it creates the instance, keeps it sized to
 * its container, applies the options, and disposes of it. It also degrades
 * honestly: when the canvas cannot be created — no GPU, a test environment —
 * it says so in text rather than showing an empty rectangle.
 */
import { BarChart, CustomChart, LineChart, ScatterChart } from 'echarts/charts';
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useRef, useState } from 'react';

import './EChart.css';

echarts.use([
  LineChart,
  BarChart,
  ScatterChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  TitleComponent,
  CanvasRenderer,
]);

export type ChartOption = echarts.EChartsCoreOption;

export interface EChartProps {
  /** The option object ECharts draws. */
  readonly option: ChartOption;
  /** The height of the plot, in pixels. */
  readonly height: number;
  /** Handlers for the ECharts events the chart reacts to. */
  readonly onEvents?: Readonly<Record<string, (params: unknown) => void>>;
  /**
   * Called once the instance exists.
   *
   * It gives the caller the handle it needs to drive the chart — resetting
   * the time range, for instance — without the wrapper knowing what for.
   */
  readonly onReady?: (chart: echarts.ECharts) => void;
}

/**
 * Whether the environment can draw.
 *
 * A canvas has no context without a graphics implementation, and ECharts
 * fails deep inside its initialisation when that is the case. The check is
 * made before the library is asked to do anything, so the component can say
 * plainly that it cannot draw — and the values are still available as a
 * table.
 */
function supportsCanvas(): boolean {
  return typeof CanvasRenderingContext2D !== 'undefined';
}

export function EChart({ option, height, onEvents, onReady }: EChartProps) {
  const container = useRef<HTMLDivElement | null>(null);
  const instance = useRef<echarts.ECharts | null>(null);
  const [drawable] = useState(supportsCanvas);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    const element = container.current;
    if (element === null || !drawable) {
      return;
    }

    let chart: echarts.ECharts;
    try {
      chart = echarts.init(element, undefined, { renderer: 'canvas' });
    } catch (error) {
      // Reporting an initialisation failure is not a cascading render: it
      // happens once, and only when the canvas could not be created at all.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFailure(error instanceof Error ? error.message : 'the canvas could not be created');
      return;
    }

    instance.current = chart;
    onReady?.(chart);

    const observer = new ResizeObserver(() => {
      chart.resize();
    });
    observer.observe(element);

    return () => {
      observer.disconnect();
      chart.dispose();
      instance.current = null;
    };
  }, [drawable, onReady]);

  useEffect(() => {
    const chart = instance.current;
    if (chart === null) {
      return;
    }
    // The time range the reader chose, and the series they hid, are theirs.
    // A new set of data, a new theme or any other change of option must not
    // throw them away.
    //
    // The series are replaced, so that no stale series survives a change of
    // data; the zoom and the legend selection are not part of the option, so
    // they stay where the reader left them.
    chart.setOption(option, { replaceMerge: ['series'] });
  }, [option]);

  useEffect(() => {
    const chart = instance.current;
    if (chart === null || onEvents === undefined) {
      return;
    }

    const handlers = Object.entries(onEvents);
    for (const [event, handler] of handlers) {
      chart.on(event, handler);
    }
    return () => {
      for (const [event, handler] of handlers) {
        chart.off(event, handler);
      }
    };
  }, [onEvents]);

  if (!drawable || failure !== null) {
    return (
      <div className="torne-echart__failure" role="status">
        {failure !== null
          ? `The chart could not be drawn: ${failure}.`
          : 'This environment cannot draw a canvas.'}{' '}
        The values are available as a table below.
      </div>
    );
  }

  return <div className="torne-echart" ref={container} style={{ height: `${height}px` }} />;
}
