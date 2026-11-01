/**
 * The supply branch.
 *
 * The page is a reading of the product the branch publishes: what it is, what
 * it holds, where it is, how it was confronted with an independent source,
 * what it bounds, and where it comes from.
 *
 * Nothing is computed here. Every number is read from the product, and the
 * page says so when a value the product did not establish is missing.
 *
 * The route is loaded on demand: a reader who never opens the branch does not
 * download the map or the chart library.
 */
import { useMemo } from 'react';

import { Breadcrumbs } from '@/components/ui/Breadcrumbs';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingState } from '@/components/ui/LoadingState';
import { CATALOGUE_SPACE } from '@/app/spaces';
import { BRANCH_ID } from '@/features/supply/branch';
import { positionedLayer, readLayers } from '@/features/supply/mapping';
import { useProduct } from '@/features/supply/resources';
import { BoundsSection } from '@/features/supply/views/BoundsSection';
import { ConfrontationSection } from '@/features/supply/views/ConfrontationSection';
import { LayersSection } from '@/features/supply/views/LayersSection';
import { PageHeader } from '@/features/supply/views/Reading';
import { ProductIdentity } from '@/features/supply/views/ProductIdentity';
import { ProvenanceSection } from '@/features/supply/views/ProvenanceSection';
import { StorageSection } from '@/features/supply/views/StorageSection';
import { TerminalsSection } from '@/features/supply/views/TerminalsSection';
import { MANIFEST } from '@/services/api/registry';
import { useResource } from '@/services/api/useResource';
import type { ApiBranch, ApiManifest } from '@/types/api/manifest';
import './SupplyRoute.css';

/**
 * The reading itself.
 *
 * A product that cannot be re-read is still a product that was read: the
 * value stays on screen, and the reader is told why it is not fresher.
 */
function SupplyReading({ branch, productId }: { readonly branch: ApiBranch; readonly productId: string }) {
  const { data: product, error, refetch } = useProduct(productId);

  if (product === null) {
    if (error !== null) {
      return (
        <ErrorState
          title="The product could not be read"
          message={error}
          onRetry={refetch}
        />
      );
    }
    return <LoadingState label="Reading the product…" />;
  }

  const layers = readLayers(product);
  const spatial = positionedLayer(layers);
  const tables = layers.filter((layer) => !layer.positioned);

  return (
    <div className="torne-supply">
      <Breadcrumbs items={[{ label: CATALOGUE_SPACE, href: '/' }, { label: branch.title }]} />

      <PageHeader
        eyebrow="Knowledge product"
        title={product.title}
        lede="What the platform has established on this supply: the layers it publishes, where they are, how they were confronted with an independent source, and what they bound."
        meta={`version ${product.version}${
          product.reference_date === null || product.reference_date === undefined
            ? ''
            : ` · reference date ${product.reference_date}`
        } · produced ${product.produced_at}`}
      />

      {error !== null ? (
        <p className="torne-supply__stale" role="status">
          The product could not be refreshed: {error}. What is on screen is the last reading.
        </p>
      ) : null}

      <ProductIdentity product={product} />
      <LayersSection product={product} />
      {spatial !== null ? <TerminalsSection product={product} layer={spatial} /> : null}
      {tables.map((layer) => (
        <StorageSection key={layer.id} product={product} layer={layer} />
      ))}
      <ConfrontationSection product={product} />
      <BoundsSection product={product} />
      <ProvenanceSection product={product} />
    </div>
  );
}

export function SupplyRoute() {
  const { data: manifest, error: manifestError, refetch: refetchManifest } =
    useResource<ApiManifest>(MANIFEST);

  const branch = useMemo(
    () => manifest?.branches.find((entry) => entry.branch_id === BRANCH_ID) ?? null,
    [manifest],
  );

  if (manifest === null) {
    if (manifestError !== null) {
      return (
        <ErrorState
          title="The catalogue could not be read"
          message={manifestError}
          onRetry={refetchManifest}
        />
      );
    }
    return <LoadingState label="Reading the branch…" />;
  }

  if (branch === null) {
    return (
      <ErrorState
        title="This branch is not in the catalogue"
        message={`The manifest does not carry a branch named "${BRANCH_ID}".`}
      />
    );
  }

  if (!branch.open) {
    return <ErrorState title="This branch is closed" message={branch.reason} />;
  }

  const productId = branch.product_ids[0];
  if (productId === undefined) {
    return (
      <ErrorState
        title="This branch publishes no product yet"
        message={branch.reason}
      />
    );
  }

  return <SupplyReading branch={branch} productId={productId} />;
}
