/**
 * The entities a layer declares as having published nothing.
 *
 * A layer that publishes states for some of the entities it covers says which
 * ones it did not. They are shown here, by name, as what they are: declared
 * absences. They are never hidden, and they are never shown as zeros.
 */
import { Badge } from '@/components/ui/Badge';
import { declaredAbsences } from '@/features/supply/mapping';
import type { SupplyLayer } from '@/features/supply/mapping';
import { NO_STATE_PUBLISHED } from '@/features/supply/mapping';
import type { ApiProductDetail } from '@/types/api/manifest';

export interface DeclaredAbsencesProps {
  readonly product: ApiProductDetail;
  readonly layer: SupplyLayer;
}

export function DeclaredAbsences({ product, layer }: DeclaredAbsencesProps) {
  const absences = declaredAbsences(product, layer.id);
  if (absences.length === 0) {
    return null;
  }

  return (
    <div className="torne-supply__absences">
      <p className="torne-supply__eyebrow">Declared absences</p>
      <p className="torne-supply__note">
        {absences.length} entities of the {layer.title} layer published no state. The product
        declares them: they are absences, not zeros, and the identifiers are the ones the platform
        publishes.
      </p>
      <ul className="torne-supply__absence-list">
        {absences.map((entity) => (
          <li key={entity} className="torne-supply__absence">
            <span className="torne-supply__absence-code">{entity}</span>
            <Badge tone="neutral" size="sm">
              {NO_STATE_PUBLISHED}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}
