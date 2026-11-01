import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ErrorState } from '@/components/ui/ErrorState';

describe('ErrorState', () => {
  it('is an alert and shows the message verbatim', () => {
    render(<ErrorState message="The explorer refused the connection." />);

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('The explorer refused the connection.');
  });

  it('offers a retry when a handler is given', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    render(<ErrorState message="The explorer refused the connection." onRetry={onRetry} />);

    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('shows no retry button when there is nothing to retry', () => {
    render(<ErrorState message="The explorer refused the connection." />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('labels the retry button as the caller wants it', () => {
    render(
      <ErrorState
        message="The explorer refused the connection."
        onRetry={() => undefined}
        retryLabel="Try again"
        title="The catalogue could not be read"
      />,
    );

    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    expect(screen.getByText('The catalogue could not be read')).toBeInTheDocument();
  });
});
