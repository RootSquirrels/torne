/**
 * The provenance.
 *
 * The lineage says what the product was built from, the production digests
 * say which files it was built from, and the payload digest says what it
 * publishes. A reader who doubts a number can follow it back to a file.
 */
import { Card } from '@/components/ui/Card';
import { Fact, Section } from '@/features/supply/views/Reading';
import type { ApiProductDetail } from '@/types/api/manifest';

export interface ProvenanceSectionProps {
  readonly product: ApiProductDetail;
}

export function ProvenanceSection({ product }: ProvenanceSectionProps) {
  const digests = Object.entries(product.provenance.production_digests);

  return (
    <Section title="The provenance" note={`${product.lineage.length} links in the lineage`}>
      <Card title="The lineage">
        <ol className="torne-supply__lineage">
          {product.lineage.map((link) => (
            <li key={`${link.kind}-${link.identifier}`} className="torne-supply__lineage-item">
              <span className="torne-supply__lineage-kind">{link.kind}</span>
              <span className="torne-supply__lineage-label">{link.label ?? link.identifier}</span>
              <span className="torne-supply__lineage-id">{link.identifier}</span>
              {link.revision !== null && link.revision !== undefined ? (
                <span className="torne-supply__lineage-revision">{link.revision}</span>
              ) : null}
            </li>
          ))}
        </ol>
      </Card>

      <Card title="The sources">
        <ul className="torne-supply__list">
          {product.provenance.sources.map((source) => (
            <li key={source.source_id}>
              <span className="torne-supply__source-publisher">{source.publisher}</span>
              <span className="torne-supply__source-dataset">{source.dataset}</span>
              <span className="torne-supply__source-units">{source.units}</span>
              <span className="torne-supply__source-access">{source.access}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="The production digests">
        <dl className="torne-supply__facts">
          {digests.map(([file, digest]) => (
            <Fact key={file} name={file}>
              <span className="torne-supply__code">{typeof digest === 'string' ? digest : String(digest)}</span>
            </Fact>
          ))}
        </dl>
      </Card>

      <Card title="The payload digest">
        <p className="torne-supply__code">{product.payload_digest}</p>
      </Card>
    </Section>
  );
}
