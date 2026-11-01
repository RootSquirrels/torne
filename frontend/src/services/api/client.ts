/**
 * The API client.
 *
 * The application reads the explorer API and nothing else: it never contacts a
 * data provider, and it never computes a scientific quantity. Every call goes
 * through `request`, so the base path, the error shape and the response
 * contract are stated in one place.
 */

import type {
  ApiAsset,
  ApiConfrontationRows,
  ApiCountryDetail,
  ApiDomain,
  ApiErrorResponse,
  ApiHealth,
  ApiManifest,
  ApiMission,
  ApiModel,
  ApiProductDetail,
  ApiProductList,
  ApiProductStates,
  ApiRegion,
  ApiResults,
  ApiSource,
  ApiSurfaceProduct,
  ApiCoverageEntry,
} from '@/types/api/manifest';

/** The canonical API prefix. */
export const API_PREFIX = '/api/v1';

/** The error raised when the API answers with a failure. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown> | null;

  constructor(status: number, body: ApiErrorResponse) {
    super(body.detail);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.error.code;
    this.details = body.error.details;
  }
}

function isErrorResponse(value: unknown): value is ApiErrorResponse {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const candidate = value as { detail?: unknown; error?: { code?: unknown } };
  return typeof candidate.detail === 'string' && typeof candidate.error?.code === 'string';
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: { Accept: 'application/json' },
    ...(signal === undefined ? {} : { signal }),
  });

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    if (isErrorResponse(payload)) {
      throw new ApiError(response.status, payload);
    }
    throw new ApiError(response.status, {
      detail: `the API answered with HTTP ${response.status}`,
      error: { code: 'unexpected_response', message: `HTTP ${response.status}`, details: null },
    });
  }

  return payload as T;
}

export const api = {
  health: (signal?: AbortSignal) => request<ApiHealth>('/health', signal),

  manifest: (signal?: AbortSignal) => request<ApiManifest>('/manifest', signal),

  domains: (signal?: AbortSignal) => request<ApiDomain[]>('/domains', signal),

  countries: (signal?: AbortSignal) => request<ApiCountryDetail[]>('/countries', signal),

  country: (code: string, signal?: AbortSignal) =>
    request<ApiCountryDetail>(`/countries/${encodeURIComponent(code)}`, signal),

  regions: (signal?: AbortSignal) => request<ApiRegion[]>('/regions', signal),

  coverage: (
    params: { domain?: string; country?: string } = {},
    signal?: AbortSignal,
  ) => {
    const query = new URLSearchParams();
    if (params.domain !== undefined) {
      query.set('domain', params.domain);
    }
    if (params.country !== undefined) {
      query.set('country', params.country);
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : '';
    return request<ApiCoverageEntry[]>(`/coverage${suffix}`, signal);
  },

  surfaceProducts: (signal?: AbortSignal) =>
    request<ApiSurfaceProduct[]>('/surface-products', signal),

  missions: (
    params: { country?: string; domain?: string; min_status?: string } = {},
    signal?: AbortSignal,
  ) => {
    const query = new URLSearchParams();
    if (params.country !== undefined) {
      query.set('country', params.country);
    }
    if (params.domain !== undefined) {
      query.set('domain', params.domain);
    }
    if (params.min_status !== undefined) {
      query.set('min_status', params.min_status);
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : '';
    return request<ApiMission[]>(`/missions${suffix}`, signal);
  },

  mission: (missionId: string, signal?: AbortSignal) =>
    request<ApiMission>(`/missions/${encodeURIComponent(missionId)}`, signal),

  assets: (
    params: { country?: string; domain?: string; kind?: string } = {},
    signal?: AbortSignal,
  ) => {
    const query = new URLSearchParams();
    if (params.country !== undefined) {
      query.set('country', params.country);
    }
    if (params.domain !== undefined) {
      query.set('domain', params.domain);
    }
    if (params.kind !== undefined) {
      query.set('kind', params.kind);
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : '';
    return request<ApiAsset[]>(`/assets${suffix}`, signal);
  },

  asset: (assetId: string, signal?: AbortSignal) =>
    request<ApiAsset>(`/assets/${encodeURIComponent(assetId)}`, signal),

  sources: (params: { domain?: string } = {}, signal?: AbortSignal) => {
    const query = new URLSearchParams();
    if (params.domain !== undefined) {
      query.set('domain', params.domain);
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : '';
    return request<ApiSource[]>(`/sources${suffix}`, signal);
  },

  source: (sourceId: string, signal?: AbortSignal) =>
    request<ApiSource>(`/sources/${encodeURIComponent(sourceId)}`, signal),

  models: (params: { executed?: boolean } = {}, signal?: AbortSignal) => {
    const query = new URLSearchParams();
    if (params.executed !== undefined) {
      query.set('executed', String(params.executed));
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : '';
    return request<ApiModel[]>(`/models${suffix}`, signal);
  },

  model: (key: string, signal?: AbortSignal) =>
    request<ApiModel>(`/models/${encodeURIComponent(key)}`, signal),

  results: (signal?: AbortSignal) => request<ApiResults>('/results', signal),

  /**
   * The published products.
   */
  products: (signal?: AbortSignal) => request<ApiProductList>('/products', signal),

  /**
   * One product: its payload, its layers, its units and its lineage.
   */
  product: (productId: string, signal?: AbortSignal) =>
    request<ApiProductDetail>(`/products/${encodeURIComponent(productId)}`, signal),

  /**
   * The states of a layer.
   *
   * Without an entity, the API serves the last published state of every
   * entity of the layer; with one, it serves the whole series of that entity.
   */
  productStates: (
    productId: string,
    params: { layer: string; entity?: string },
    signal?: AbortSignal,
  ) => {
    const query = new URLSearchParams();
    query.set('layer', params.layer);
    if (params.entity !== undefined) {
      query.set('entity', params.entity);
    }
    return request<ApiProductStates>(
      `/products/${encodeURIComponent(productId)}/states?${query.toString()}`,
      signal,
    );
  },

  /**
   * The confrontation of the product with an independent source.
   */
  productConfrontation: (productId: string, signal?: AbortSignal) =>
    request<ApiConfrontationRows>(
      `/products/${encodeURIComponent(productId)}/confrontation`,
      signal,
    ),
};

export type Api = typeof api;
