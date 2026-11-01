/**
 * The layers the product publishes.
 *
 * A layer is a set of states: the entities it covers, the period it covers
 * them over, and the measures it publishes for them. The unit of a measure is
 * read from the product's own units, and written once: the page never writes
 * a unit beside a number that the product has not declared.
 */
import { Card } from '@/components/ui/Card';
import { formatValue } from '@/features/supply/mapping';
import { readLayers } from '@/features/supply/mapping';
import type { SupplyLayer } from '@/features/supply/mapping';
import { Section } from '@/features/supply/views/Reading';
import type { ApiProductDetail } from '@/types/api/manifest';

export interface LayersSectionProps {
  readonly product: ApiProductDetail;
}

/** The period a layer covers, in the words the product uses. */
function period(layer: SupplyLayer): string {
  const { start, end } = layer.window;
  if (start === null || end === null) {
    return 'the period is not established';
  }
  return start === end ? start : `${start} → ${end}`;
}

function LayerCard({ layer }: { readonly layer: SupplyLayer }) {
  return (
    <Card title={layer.title} subtitle={period(layer)}>
      <dl className="torne-supply__facts">
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">States</dt>
          <dd className="torne-supply__fact-value">{formatValue(layer.window.states)}</dd>
        </div>
        <div className="torne-supply__fact">
          <dt className="torne-supply__fact-name">Entities</dt>
          <dd className="torne-supply__fact-value">{formatValue(layer.window.entities)}</dd>
        </div>
        {layer.file !== null ? (
          <div className="torne-supply__fact">
            <dt className="torne-supply__fact-name">File</dt>
            <dd className="torne-supply__fact-value">{layer.file}</dd>
          </div>
        ) : null}
      </dl>

      <div className="torne-supply__measures">
        <p className="torne-supply__eyebrow">Measures</p>
        <ul className="torne-supply__measure-list">
          {layer.measures.map((measure) => (
            <li key={measure.column} className="torne-supply__measure">
              <span className="torne-supply__measure-label">{measure.label}</span>
              {measure.unit !== null ? (
                <span className="torne-supply__measure-unit">{measure.unit}</span>
              ) : null}
            </li>
          ))}
        </ul>
      </div>

      {layer.flags.length > 0 ? (
        <div className="torne-supply__measures">
          <p className="torne-supply__eyebrow">Flags</p>
          <ul className="torne-supply__measure-list">
            {layer.flags.map((flag) => (
              <li key={flag.column} className="torne-supply__measure">
                <span className="torne-supply__measure-label">{flag.label}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Card>
  );
}

export function LayersSection({ product }: LayersSectionProps) {
  const layers = readLayers(product);

  return (
    <Section title="The layers" note={layers.map((layer) => layer.title).join(' · ')}>
      {layers.map((layer) => (
        <LayerCard key={layer.id} layer={layer} />
      ))}
    </Section>
  );
}
