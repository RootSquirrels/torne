/**
 * Escaping for the HTML that a chart builds.
 *
 * A tooltip and a map popup are HTML: a canvas has no other way to show a
 * label, and a popup has no other way to show a table. The text put into that
 * HTML comes from the API — a mission name, a country name, a source label —
 * and it is **escaped**, because a label that carries markup must be read as
 * text and never interpreted as markup.
 *
 * The repository forbids generating HTML strings for components; a tooltip is
 * the one place where the platform leaves no choice. Escaping is what makes
 * that place safe.
 */

/** The characters that carry meaning in HTML. */
const ENTITIES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

/** Escape a string, for use in HTML text or in an attribute value. */
export function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ENTITIES[character] ?? character);
}
