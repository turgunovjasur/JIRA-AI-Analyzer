import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { TeamAnalyticsDashboard } from './team-analytics-dashboard';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('Team Analytics view', () => {
  it('shows row ranges, page numbers and the next page size', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      const offset = Number(new URL(url, 'https://example.test').searchParams.get('offset') || 0);
      const count = Math.min(20, 45 - offset);
      return { ok: true, json: async () => ({
        tasks: Array.from({ length: count }, (_, index) => ({ jira_source: 'test', issue_id: String(offset + index),
          issue_key: `TEST-${offset + index}`, is_working: false, deleted: false, total_seconds: 0,
          assignee_seconds: 0, work_days: 0, story_points: 1, intervals: [] })),
        assignees: [], daily_hours: 8, weekly_hours: 40, working_status: 'In Progress',
        total: 45, limit: 20, offset, generated_at: '2026-10-06T00:00:00Z',
        summary: { worked_seconds: 0, task_points: 45, work_days: 0, missing_points: 0, task_estimates: [] },
      }) };
    }));
    render(<TeamAnalyticsDashboard />);
    await screen.findByText(/1–20.*45.*20 ta qator/);
    expect(screen.getByText(/Sahifa 1 \/ 3/)).toBeTruthy();
    expect(screen.getByText(/Keyingi sahifada: 20 ta/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    await screen.findByText(/21–40.*45.*20 ta qator/);
    expect(screen.getByText(/Keyingi sahifada: 5 ta/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Keyingi' }));
    await screen.findByText(/41–45.*45.*5 ta qator/);
    expect((screen.getByRole('button', { name: 'Keyingi' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('applies temporary points only on calculation and resets on another assignee', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ tasks: [], assignees: [], daily_hours: 8, weekly_hours: 40,
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
