import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { TeamAnalyticsDashboard } from './team-analytics-dashboard';

afterEach(() => vi.unstubAllGlobals());

describe('Team Analytics view', () => {
  it('applies temporary points only on calculation and resets on another assignee', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ tasks: [], assignees: [], daily_hours: 8,
      working_status: 'In Progress', total: 0, limit: 20, offset: 0, generated_at: new Date().toISOString(),
      summary: { worked_seconds: 0, task_points: 0, work_days: 0, missing_points: 0, task_estimates: [] } }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<TeamAnalyticsDashboard />);
    await waitFor(() => expect(screen.queryByRole('status')).toBeNull());
    fireEvent.click(screen.getByRole('button', { name: 'Demo' }));
    fireEvent.change(screen.getByLabelText('Ijrochi'), { target: { value: '["demo","demo-ali"]' } });
    fireEvent.change(screen.getByLabelText('Kunlik point'), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Hisoblash' }));
    expect(screen.getByText(/Jadval 2 point\/kun bo‘yicha hisoblangan/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Kunlik point'), { target: { value: '4' } });
    expect(screen.getByText(/Jadval 2 point\/kun bo‘yicha hisoblangan/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Hisoblash' }));
    expect(screen.getByText(/Jadval 4 point\/kun bo‘yicha hisoblangan/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Ijrochi'), { target: { value: '["demo","demo-vali"]' } });
    expect((screen.getByLabelText('Kunlik point') as HTMLInputElement).value).toBe('');
    expect(fetchMock.mock.calls.every(([url]) => !String(url).includes('point'))).toBe(true);
  });
});
