/**
 * The HTML escaping.
 *
 * A tooltip and a map popup are HTML: the canvas has no other way to show a
 * label. The text they carry comes from the API, so it is escaped — a label
 * that carries markup must be read as text, never interpreted as markup.
 */
import { describe, expect, it } from 'vitest';

import { escapeHtml } from '@/components/visualization/html';

describe('the HTML escaping', () => {
  it('escapes the characters that carry meaning', () => {
    expect(escapeHtml('<script>alert("x")</script>')).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;',
    );
  });

  it('escapes the ampersand before the rest', () => {
    expect(escapeHtml('a & b')).toBe('a &amp; b');
    expect(escapeHtml('&lt;')).toBe('&amp;lt;');
  });

  it('escapes a single quote, which an attribute may carry', () => {
    expect(escapeHtml("O'Brien")).toBe('O&#39;Brien');
  });

  it('leaves ordinary text alone', () => {
    expect(escapeHtml('Débit — 12 m³/s')).toBe('Débit — 12 m³/s');
  });
});
