import type { ApiRef, RefKind } from '@/types/api/manifest';

import './ProvenanceLink.css';

export interface ProvenanceLinkProps {
  /** The reference to render. */
  reference: ApiRef;
  /** Called with the target when a mission reference is activated. */
  onNavigate?: (target: string) => void;
}

/** The kind of a reference, in words, for the tooltip. */
const KIND_TITLES: Record<RefKind, string> = {
  mission: 'Mission reference',
  document: 'Document reference — opens in a new tab',
  script: 'Script reference — opens in a new tab',
  implementation: 'Implementation reference',
  record: 'Record reference',
};

/**
 * A reference to the evidence behind a fact.
 *
 * The kind of the reference decides what it is, because the kinds answer
 * different questions: a document or a script is a file that opens in a new
 * tab, a mission is an entity of this application and is navigated to
 * in-place, an implementation is a name in the code, and a record is a
 * persisted result.
 *
 * A reference that carries no URL is never rendered as a broken link: the
 * target is shown as plain text instead, and the kind still explains itself
 * through the tooltip.
 */
export function ProvenanceLink({ reference, onNavigate }: ProvenanceLinkProps) {
  const { kind, target, url } = reference;
  const title = KIND_TITLES[kind];

  if (kind === 'document' || kind === 'script') {
    if (url === null) {
      return (
        <span className="torne-provenance-link" title={title}>
          {target}
        </span>
      );
    }
    return (
      <a
        className="torne-provenance-link"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        title={title}
      >
        {target}
      </a>
    );
  }

  if (kind === 'mission') {
    if (onNavigate === undefined) {
      return (
        <span className="torne-provenance-link" title={title}>
          {target}
        </span>
      );
    }
    return (
      <button
        type="button"
        className="torne-provenance-link"
        onClick={() => {
          onNavigate(target);
        }}
        title={title}
      >
        {target}
      </button>
    );
  }

  if (kind === 'implementation') {
    return (
      <code className="torne-provenance-link torne-provenance-link--code" title={title}>
        {target}
      </code>
    );
  }

  return (
    <span className="torne-provenance-link" title={title}>
      {target}
    </span>
  );
}
