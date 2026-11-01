/**
 * The resources the supply branch reads.
 *
 * A product is a record the catalogue names, so its identifier is not known
 * before the manifest has been read. The resources are therefore declared
 * here, once the product is known, and read by key everywhere else — the
 * store keeps the value, so a page that comes back to a product reads what
 * it already had.
 *
 * The declaration is idempotent: the store never throws away a value that has
 * been produced, so declaring a resource again is harmless, and a reader who
 * stays on the page keeps the last value on screen when a refresh fails.
 */
import { api } from '@/services/api/client';
import { resources } from '@/services/api/registry';
import { useResource } from '@/services/api/useResource';
import type { Resource } from '@/services/api/useResource';
import type { ApiConfrontationRows, ApiProductDetail, ApiProductStates } from '@/types/api/manifest';

/** The key under which a product is read. */
export function productKey(productId: string): string {
  return `product:${productId}`;
}

/**
 * The key under which the states of a layer are read.
 *
 * Without an entity, the states are the last published state of every entity
 * of the layer; with one, they are the whole series of that entity.
 */
export function productStatesKey(productId: string, layer: string, entity: string | undefined): string {
  return entity === undefined
    ? `product-states:${productId}:${layer}`
    : `product-states:${productId}:${layer}:${entity}`;
}

/** The key under which the confrontation of a product is read. */
export function productConfrontationKey(productId: string): string {
  return `product-confrontation:${productId}`;
}

/**
 * Declare the resources of a product.
 *
 * The catalogue changes when a product is published: rarely, and never in the
 * middle of a reading.
 */
export function declareProduct(productId: string): void {
  resources.register(
    productKey(productId),
    (signal) => api.product(productId, signal),
    { freshnessMs: 30_000 },
  );
  resources.register(
    productConfrontationKey(productId),
    (signal) => api.productConfrontation(productId, signal),
    { freshnessMs: 30_000 },
  );
}

/** Declare the states of one layer of a product. */
export function declareProductStates(
  productId: string,
  layer: string,
  entity: string | undefined,
): void {
  resources.register(
    productStatesKey(productId, layer, entity),
    (signal) => api.productStates(productId, { layer, ...(entity === undefined ? {} : { entity }) }, signal),
    { freshnessMs: 30_000 },
  );
}

/** Read a product: what it holds, and the lineage that produced it. */
export function useProduct(productId: string): Resource<ApiProductDetail> {
  declareProduct(productId);
  return useResource<ApiProductDetail>(productKey(productId));
}

/** Read the states of a layer of a product. */
export function useProductStates(
  productId: string,
  layer: string,
  entity: string | undefined,
): Resource<ApiProductStates> {
  declareProductStates(productId, layer, entity);
  return useResource<ApiProductStates>(productStatesKey(productId, layer, entity));
}

/** Read the confrontation of a product with an independent source. */
export function useProductConfrontation(productId: string): Resource<ApiConfrontationRows> {
  declareProduct(productId);
  return useResource<ApiConfrontationRows>(productConfrontationKey(productId));
}
