import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DataTable } from '@/components/data/DataTable';
import type { DataTableColumn } from '@/components/data/DataTable';

interface MissionRow {
  readonly id: string;
  readonly name: string;
  readonly rank: number;
}

const ALPHA: MissionRow = { id: '1', name: 'Alpha', rank: 2 };
const BETA: MissionRow = { id: '2', name: 'Beta', rank: 4 };
const ROWS: MissionRow[] = [ALPHA, BETA];

const COLUMNS: DataTableColumn<MissionRow>[] = [
  { key: 'name', header: 'Mission' },
  { key: 'rank', header: 'Rank', align: 'end' },
];

describe('DataTable', () => {
  it('renders a captioned table with column headers and rows', () => {
    render(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        getRowKey={(row) => row.id}
        caption="Missions"
      />,
    );

    expect(screen.getByRole('table', { name: 'Missions' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Mission' })).toHaveAttribute('scope', 'col');
    expect(screen.getByRole('columnheader', { name: 'Rank' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: 'Alpha' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '2' })).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(3);
  });

  it('renders the rows through the renderer of a column', () => {
    render(
      <DataTable
        columns={[
          { key: 'name', header: 'Mission', render: (row) => row.name.toUpperCase() },
          { key: 'rank', header: 'Rank' },
        ]}
        rows={ROWS}
        getRowKey={(row) => row.id}
      />,
    );

    expect(screen.getByRole('cell', { name: 'ALPHA' })).toBeInTheDocument();
  });

  it('shows the loading state instead of the rows', () => {
    render(
      <DataTable columns={COLUMNS} rows={ROWS} getRowKey={(row) => row.id} loading />,
    );

    expect(screen.getByRole('status')).toHaveTextContent('Loading…');
    expect(screen.queryByRole('cell', { name: 'Alpha' })).not.toBeInTheDocument();
  });

  it('shows the error instead of the rows', () => {
    render(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        getRowKey={(row) => row.id}
        error="The explorer refused the connection."
      />,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('The explorer refused the connection.');
    expect(screen.queryByRole('cell', { name: 'Alpha' })).not.toBeInTheDocument();
  });

  it('shows an empty state when there is no row', () => {
    render(<DataTable columns={COLUMNS} rows={[]} getRowKey={(row) => row.id} />);

    expect(screen.getByText('Nothing to show')).toBeInTheDocument();
  });

  it('shows the empty state the caller provides', () => {
    render(
      <DataTable
        columns={COLUMNS}
        rows={[]}
        getRowKey={(row) => row.id}
        empty={<p>No mission covers this country.</p>}
      />,
    );

    expect(screen.getByText('No mission covers this country.')).toBeInTheDocument();
  });

  it('makes the first cell a button when the rows are interactive', async () => {
    const user = userEvent.setup();
    const onRowClick = vi.fn<(row: MissionRow) => void>();

    render(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        getRowKey={(row) => row.id}
        onRowClick={onRowClick}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Alpha' }));
    expect(onRowClick).toHaveBeenCalledWith(ALPHA);

    expect(screen.queryByRole('button', { name: '2' })).not.toBeInTheDocument();
  });

  it('leaves the rows without a button when they are not interactive', () => {
    render(<DataTable columns={COLUMNS} rows={ROWS} getRowKey={(row) => row.id} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
