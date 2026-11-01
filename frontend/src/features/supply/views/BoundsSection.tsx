/**
 * The bounds.
 *
 * Two of the quantities the product publishes are bounds and not
 * measurements. They are shown as what they are: a direction, and the
 * statement that says why the true value lies there. They are never shown as
 * plain numbers, because a bound that looks like a measurement is read as one.
 */
import { Badge } from '@/components/ui/Badge';
import type { BadgeTone } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Section } from '@/features/supply/views/Reading';
import type { ApiProductDetail } from '@/types/api/manifest';

/**
 * The register a bound is shown in.
 *
 * The direction is written in words beside the colour, so the colour never
 * carries it alone.
 */
function toneOf(direction: string): BadgeTone {
  return direction === 'lower' ? 'info' : direction === 'upper' ? 'warning' : 'neutral';
}

export interface BoundsSectionProps {
  readonly product: ApiProductDetail;
}

export function BoundsSection({ product }: BoundsSectionProps) {
  return (
    <Section
      title="The bounds"
      note={`${product.bounds.length} quantities are bounds, not measurements`}
    >
      {product.bounds.map((bound) => (
        <Card key={`${bound.quantity}-${bound.direction}`} title={bound.quantity}>
          <p className="torne-supply__badge-line">
            <Badge tone={toneOf(bound.direction)}>
              {bound.direction === 'lower' ? 'lower bound' : bound.direction === 'upper' ? 'upper bound' : bound.direction}
            </Badge>
          </p>
          <p className="torne-supply__paragraph">{bound.statement}</p>
        </Card>
      ))}
    </Section>
  );
}
