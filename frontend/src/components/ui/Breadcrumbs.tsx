import './Breadcrumbs.css';

export interface BreadcrumbItem {
  /** The visible text. */
  label: string;
  /** When given, the item is a link. */
  href?: string;
  /** When given and no `href` is, the item is a button. */
  onClick?: () => void;
}

export interface BreadcrumbsProps {
  items: ReadonlyArray<BreadcrumbItem>;
}

/**
 * The breadcrumb trail.
 *
 * The trail is a navigation landmark, so it is labelled. The last item is the
 * current page: it carries `aria-current="page"` and is rendered as plain
 * text, never as a link to where the user already is. An item with a `href`
 * is a link, an item with only an `onClick` is a button, and an item with
 * neither is plain text.
 *
 * States: link (normal, hover, focus), current page.
 */
export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="torne-breadcrumbs" aria-label="Breadcrumb">
      <ol className="torne-breadcrumbs__list">
        {items.map((item, index) => {
          const isCurrent = index === items.length - 1;

          return (
            <li className="torne-breadcrumbs__item" key={`${item.label}-${index}`}>
              {index > 0 && (
                <span className="torne-breadcrumbs__separator" aria-hidden="true">
                  /
                </span>
              )}
              {isCurrent ? (
                <span className="torne-breadcrumbs__current" aria-current="page">
                  {item.label}
                </span>
              ) : item.href !== undefined ? (
                <a className="torne-breadcrumbs__link" href={item.href}>
                  {item.label}
                </a>
              ) : item.onClick !== undefined ? (
                <button
                  type="button"
                  className="torne-breadcrumbs__button"
                  onClick={item.onClick}
                >
                  {item.label}
                </button>
              ) : (
                <span className="torne-breadcrumbs__text">{item.label}</span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
