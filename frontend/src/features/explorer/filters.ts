/**
 * The filters of the explorer.
 *
 * The filters narrow what the map and the lists show. They live in the URL,
 * because a reader who has narrowed the view to one domain and one status is
 * looking at something worth sharing.
 *
 * A filter never hides a fact: it hides a **row**. The map keeps colouring
 * every country by the status its missions earned, and the lists say what a
 * country holds even when the filter leaves nothing to show.
 */
import type { ApiAsset, ApiMission, ApiStatusEntry } from '@/types/api/manifest';

export interface ExplorerFilters {
  readonly domain: string;
  readonly status: string;
  readonly kind: string;
}

export const EMPTY_FILTERS: ExplorerFilters = { domain: '', status: '', kind: '' };

export function statusRank(statuses: readonly ApiStatusEntry[], label: string): number {
  return statuses.find((entry) => entry.status === label)?.rank ?? 0;
}

export function missionMatches(
  mission: ApiMission,
  filters: ExplorerFilters,
  statuses: readonly ApiStatusEntry[],
): boolean {
  if (filters.domain !== '' && !mission.domain_ids.includes(filters.domain)) {
    return false;
  }
  if (filters.status !== '' && mission.status_rank < statusRank(statuses, filters.status)) {
    return false;
  }
  return true;
}

export function assetMatches(
  asset: ApiAsset,
  filters: ExplorerFilters,
  missions: readonly ApiMission[],
  statuses: readonly ApiStatusEntry[],
): boolean {
  if (filters.domain !== '' && asset.domain_id !== filters.domain) {
    return false;
  }
  if (filters.kind !== '' && asset.kind !== filters.kind) {
    return false;
  }
  const related = missions.filter((mission) => asset.mission_ids.includes(mission.mission_id));
  return related.length === 0 || related.some((mission) => missionMatches(mission, filters, statuses));
}

/**
 * The status a country has earned.
 *
 * It is the highest status among the missions of that country. A
 * region-wide mission never colours a country: that coverage is not a
 * national status.
 */
export function countryRank(
  code: string,
  missions: readonly ApiMission[],
  filters: ExplorerFilters,
  statuses: readonly ApiStatusEntry[],
): number {
  const ranks = missions
    .filter((mission) => mission.countries.includes(code) && missionMatches(mission, filters, statuses))
    .map((mission) => mission.status_rank);
  return ranks.length > 0 ? Math.max(...ranks) : 0;
}
