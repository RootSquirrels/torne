/**
 * What this is.
 *
 * The product describes itself, and this section does not paraphrase it: the
 * domain of validity and the uncertainty are the product's own sentences, and
 * the facts around them — the version, the status, the reference date — are
 * the ones the API publishes.
 */
import { Badge } from '@/components/ui/Badge';
import type { BadgeTone } from '@/components/ui/Badge';
import { formatRelative, NOT_ESTABLISHED } from '@/features/supply/mapping';
import { Fact, Section } from '@/features/supply/views/Reading';
import type { ApiProductDetail } from '@/types/api/manifest';

/**
 * The register a status is shown in.
 *
 * The word the product publishes is always written beside the colour, so the
 * colour never carries the status on its own.
 */
const STATUS_TONES: Readonly<Record<string, BadgeTone>> = {
  usable: 'success',
  degraded: 'warning',
  withdrawn: 'danger',
  inconclusive: 'neutral',
};

export interface ProductIdentityProps {
  readonly product: ApiProductDetail;
}

export function ProductIdentity({ product }: ProductIdentityProps) {
  const validation = product.validation;
  const tone = STATUS_TONES[product.status] ?? 'neutral';

  return (
    <Section title="What this is" note={`version ${product.version}`}>
      <div className="torne-supply__status">
        <p className="torne-supply__eyebrow">Status</p>
        <div className="torne-supply__status-value">
          <Badge tone={tone}>{product.status}</Badge>
          <span className="torne-supply__status-evidence">
            <span className="torne-supply__eyebrow">Status supported by</span>
            <span>
              the confrontation with an independent source — {validation.comparisons} comparisons, median
              relative difference {formatRelative(validation.median_relative_difference)}
            </span>
          </span>
        </div>
      </div>

      <dl className="torne-supply__facts">
        <Fact name="Title">{product.title}</Fact>
        <Fact name="Version">{product.version}</Fact>
        <Fact name="Status">{product.status}</Fact>
        <Fact name="Reference date">
          {product.reference_date === null || product.reference_date === undefined
            ? NOT_ESTABLISHED
            : product.reference_date}
        </Fact>
        <Fact name="Nature">{product.nature}</Fact>
        <Fact name="Produced at">{product.produced_at}</Fact>
        <Fact name="Payload files">
          {product.payload_files.length === 0 ? 'none' : product.payload_files.join(', ')}
        </Fact>
      </dl>

      <div className="torne-supply__prose">
        <p className="torne-supply__eyebrow">Domain of validity</p>
        <p className="torne-supply__paragraph">{product.domain_of_validity}</p>
      </div>

      <div className="torne-supply__prose">
        <p className="torne-supply__eyebrow">Uncertainty</p>
        <p className="torne-supply__paragraph">{product.uncertainty}</p>
      </div>
    </Section>
  );
}
