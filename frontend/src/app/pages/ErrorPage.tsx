/**
 * The page shown when a route could not be resolved.
 */
import { Link, useRouteError } from 'react-router-dom';

import './ErrorPage.css';

export function ErrorPage() {
  const error = useRouteError();
  const message =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : 'The page could not be shown.';

  return (
    <div className="torne-error-page">
      <h1 className="torne-error-page__title">This page could not be shown</h1>
      <p className="torne-error-page__message">{message}</p>
      <p>
        <Link to="/">Back to the overview</Link>
      </p>
    </div>
  );
}
