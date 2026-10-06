"use client";

import { useMemo } from "react";
import type { AnalyticsTask } from "@/lib/team-analytics-types";
import { duration, groupIntervalsByDay } from "@/lib/team-analytics-time";

export function TeamAnalyticsTaskDetails({ task, assigneeId, showAll, timeZone }: {
  task: AnalyticsTask; assigneeId: string | null; showAll: boolean; timeZone?: string;
}) {
  const days = useMemo(() => groupIntervalsByDay(task.intervals.filter(interval =>
    assigneeId === null || interval.assignee_id === assigneeId), timeZone), [task.intervals, assigneeId, timeZone]);
  const total = days.reduce((sum, day) => sum + day.seconds, 0);
  return <div className="rounded-md bg-muted/40 p-4">
    {days.length === 0 ? <p className="mt-3 text-sm text-muted-foreground">Hisoblangan vaqt hali yo‘q.</p> :
      <div className="space-y-4">{days.map(day => <div key={day.date}>
        <p className="font-semibold">{day.date} / jami: {duration(day.seconds)}</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 tabular-nums">{day.intervals.map((interval, index) => <li key={index}>
          {interval.start} – {interval.isOpen ? "hozir" : interval.end}
          {showAll && <span className="ml-3 text-muted-foreground">{interval.assigneeName}</span>}
        </li>)}</ul>
      </div>)}</div>}
    <hr className="my-4 border-border" />
    <p className="font-semibold">Jami: {duration(total)}</p>
  </div>;
}
