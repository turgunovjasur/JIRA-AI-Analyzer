"use client";

import { Fragment, useMemo, useState } from "react";
import { TeamAnalyticsSettings } from "@/components/team-analytics-settings";
import { TeamAnalyticsTaskDetails } from "@/components/team-analytics-task-details";
import { ANALYTICS_PAGE_SIZE as PAGE_SIZE, useTeamAnalytics } from "@/hooks/use-team-analytics";
import { calculateDelay, parseAssignee } from "@/lib/team-analytics-calculations";
import { duration, numberLabel } from "@/lib/team-analytics-time";
import { sprintKey, sprintLabel, sprintWindow } from "@/lib/team-analytics-sprints";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AnalyticsSettingsValue } from "@/lib/team-analytics-types";


export function TeamAnalyticsDashboard() {
  const [assignee, setAssignee] = useState("all");
  const [sprint, setSprint] = useState("all");
  // Only this open view uses the entered points. Never persist or send them to the API.
  const [dailyPoints, setDailyPoints] = useState("");
  const [calculatedPoints, setCalculatedPoints] = useState<number | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [demoSettings, setDemoSettings] = useState<AnalyticsSettingsValue>({ working_status: "In Progress", daily_hours: 8 });
  const [showSettings, setShowSettings] = useState(false);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const { snapshot, catalog, loading, error } = useTeamAnalytics(assignee, offset, refresh, demo, demoSettings, sprint);

  const tasks = snapshot?.tasks || [];
  const showAssigneeColumn = assignee === "all" && (snapshot?.summary.assignee_count ?? new Set(tasks.map(task => task.assignee_id || "unassigned")).size) > 1;
  const assignees = catalog?.assignees || [];
  const sprints = catalog?.sprints || [];
  const selectedPerson = assignees.find(person => JSON.stringify([person.jira_source, person.assignee_id]) === assignee);
  const isPersonSelected = assignee !== "all" && assignee !== "unassigned";
  const selectedId = assignee === "all" ? null : assignee === "unassigned" ? "" : parseAssignee(assignee)[1];
  const enteredPoints = Number(dailyPoints);
  const validEnteredPoints = isPersonSelected && dailyPoints.trim() !== "" && Number.isFinite(enteredPoints) && enteredPoints > 0 && enteredPoints <= 10000;
  const pointsNumber = calculatedPoints ?? 0;
  const validPoints = isPersonSelected && calculatedPoints !== null;
  const delay = useMemo(() => validPoints && snapshot
    ? calculateDelay(snapshot.summary.task_estimates, snapshot.daily_hours, pointsNumber) : null,
    [validPoints, pointsNumber, snapshot]);
  const nameCounts = new Map<string, number>();
  for (const person of assignees) nameCounts.set(person.assignee_name, (nameCounts.get(person.assignee_name) || 0) + 1);
  const sprintNameCounts = new Map<string, number>();
  for (const item of sprints) if (item.name) sprintNameCounts.set(item.name, (sprintNameCounts.get(item.name) || 0) + 1);

  const changeAssignee = (value: string) => {
    if (value === assignee && offset === 0) return;
    if (value !== assignee) { setDailyPoints(""); setCalculatedPoints(null); }
    setAssignee(value); setOffset(0); setExpandedTask(null);
  };

  return <div className="space-y-6">
    <style>{`
      .team-analytics-table-scroll { overflow: visible; }
      .team-analytics-table-scroll thead {
        position: sticky;
        top: 64px;
        z-index: 20;
        background: var(--bg-layer);
        box-shadow: 0 1px 0 var(--line-strong);
      }
      @media (max-width: 767px) {
        .team-analytics-table-scroll {
          overflow: auto;
          max-height: calc(100dvh - 160px);
        }
        .team-analytics-table-scroll thead { top: 0; }
      }
    `}</style>
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-xl font-semibold">Team Analytics</h1>
          <p className="mt-2 text-sm text-muted-foreground">Hisoblash statusi: {snapshot?.working_status || "…"}. Bir ish kuni: {snapshot?.daily_hours ?? 8} soat.</p></div>
        <div className="flex flex-wrap gap-3">
          <Button variant="soft" aria-expanded={showSettings} onClick={() => setShowSettings(value => !value)}>Settings</Button>
          <Button disabled={loading} onClick={() => setRefresh(value => value + 1)}>Yangilash</Button>
          <Button variant={demo ? "primary" : "soft"} aria-pressed={demo} onClick={() => {
            setDemo(value => !value); setSprint("all"); setAssignee("all"); setDailyPoints(""); setCalculatedPoints(null); setExpandedTask(null);
            setOffset(0);
          }}>{demo ? "Demo: yoqilgan" : "Demo"}</Button>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{demo ? "Demo rejimi: soxta tasklar va ijrochilar." : "Ma’lumotlar Jira signallaridan avtomatik yig‘iladi."}</p>
    </Card>
    {showSettings && snapshot && <TeamAnalyticsSettings key={demo ? "demo" : "live"}
      workingStatus={snapshot.working_status} dailyHours={snapshot.daily_hours} demo={demo} onSaved={values => {
        if (demo) setDemoSettings(values);
        else setRefresh(value => value + 1);
      }} />}
    {catalog && <Card>
      <div className="flex flex-wrap items-end gap-4">
        <div className="space-y-2">
          <label htmlFor="sprint-filter" className="block text-sm font-medium">Sprint</label>
          <select id="sprint-filter" value={sprint} disabled={loading} onChange={event => {
            setSprint(event.target.value); setOffset(0); setExpandedTask(null);
          }} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm sm:w-72">
            <option value="all">Barcha sprintlar</option>
            {sprints.map(item => <option key={sprintKey(item)} value={sprintKey(item)}
              disabled={!sprintWindow(item, Date.parse(catalog.generated_at))}>
              {sprintLabel(item, (sprintNameCounts.get(item.name || "") || 0) > 1)}
            </option>)}
          </select>
        </div>
        <div className="space-y-2">
          <label htmlFor="assignee-filter" className="block text-sm font-medium">Ijrochi</label>
          <select id="assignee-filter" value={assignee} onChange={event => changeAssignee(event.target.value)}
            className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm sm:w-64">
            <option value="all">Barcha ijrochilar</option>
            <option value="unassigned">Biriktirilmagan</option>
            {assignees.map(person => {
              const key = JSON.stringify([person.jira_source, person.assignee_id]);
              return <option key={key} value={key}>{person.assignee_name}{(nameCounts.get(person.assignee_name) || 0) > 1 ? ` (${person.jira_source} · ${person.assignee_id})` : ""}</option>;
            })}
          </select>
        </div>
        {isPersonSelected && <div className="space-y-2">
          <label htmlFor="daily-points" className="block text-sm font-medium">Kunlik point</label>
          <input id="daily-points" type="number" min="0.01" max="10000" step="0.01" value={dailyPoints}
            onChange={event => setDailyPoints(event.target.value)} placeholder="Masalan, 5" aria-describedby="daily-points-help"
            className="h-10 w-40 rounded-md border border-input bg-background px-3 text-sm" />
        </div>}
        <Button disabled={loading || Boolean(error) || !validEnteredPoints}
          onClick={() => setCalculatedPoints(enteredPoints)}>Hisoblash</Button>
      </div>
      {snapshot?.selected_sprint && snapshot.sprint_window && <p className="mt-3 text-sm text-muted-foreground">
        {snapshot.selected_sprint.name || "Tanlangan sprint"}: {new Date(snapshot.sprint_window.started_at).toLocaleDateString('en-GB', { timeZone: 'Asia/Tashkent' }).replaceAll('/', '.')}
        {" – "}{snapshot.selected_sprint.state === "active" ? "hozir" : new Date(snapshot.sprint_window.ended_at).toLocaleDateString('en-GB', { timeZone: 'Asia/Tashkent' }).replaceAll('/', '.')}
        . Faqat shu sprint davomidagi vaqt hisoblanadi.
      </p>}
      {isPersonSelected && <p id="daily-points-help" className="mt-3 text-sm text-muted-foreground">
        Kunlik pointni kiriting va Hisoblash tugmasini bosing. Qiymat faqat shu jadval hisobida ishlatiladi va saqlanmaydi.
      </p>}
      {validPoints && <p className="mt-2 text-sm text-muted-foreground">
        Jadval {numberLabel(pointsNumber)} point/kun bo‘yicha hisoblangan.
        {(!validEnteredPoints || enteredPoints !== calculatedPoints) && " Yangi qiymatni qo‘llash uchun Hisoblash tugmasini bosing."}
      </p>}
      {isPersonSelected && dailyPoints && !validEnteredPoints && <p role="alert" className="mt-2 text-sm text-destructive">Kunlik point 0 dan katta va 10000 dan oshmagan son bo‘lishi kerak.</p>}
    </Card>}
    {error && <p role="alert" className="text-destructive">{error}</p>}
    {loading && <p role="status">Yuklanmoqda…</p>}
    {!loading && !error && snapshot && <>
      <p className="text-sm text-muted-foreground">{isPersonSelected ? `${selectedPerson?.assignee_name || "Ijrochi"} uchun hisob` : "Tasklar hisobi"} · {snapshot.total} ta task · Yangilangan: {new Date(snapshot.generated_at).toLocaleString()}</p>
      {tasks.length === 0 ? <Card>{assignee === "all" && sprint === "all" ? "Hali Jira signallari kelmagan." : "Tanlangan filtrlarga mos tasklar topilmadi."}</Card> : <Card>
        <div className="team-analytics-table-scroll"><table className="w-full text-left text-sm">
          <thead><tr className="border-b">
            <th className="p-3">Task</th>{showAssigneeColumn && <th className="p-3">Ijrochi</th>}<th className="p-3">Status</th>
            <th className="p-3">{assignee === "all" ? "Jami vaqt" : "Ijrochi ishlagan vaqt"}</th>
            <th className="p-3">Task pointi</th><th className="p-3">Vaqtga teng point</th>
          </tr></thead>
          <tbody>{tasks.map(task => {
            const key = JSON.stringify([task.jira_source, task.issue_id]);
            const expanded = expandedTask === key;
            const timePoints = validPoints ? task.work_days * pointsNumber : null;
            const comparison = timePoints === null || task.story_points == null ? null
              : timePoints > task.story_points ? "over" : timePoints < task.story_points ? "under" : "equal";
            const pointComparisonLabel = comparison === "over" ? "Task pointidan katta"
              : comparison === "under" ? "Task pointidan kichik" : comparison === "equal" ? "Task pointiga teng" : undefined;
            const detailsId = `task-details-${encodeURIComponent(task.jira_source)}-${encodeURIComponent(task.issue_id)}`;
            return <Fragment key={key}>
              <tr className="cursor-pointer border-b align-top focus-visible:outline-2 focus-visible:outline-ring hover:bg-muted/40"
                tabIndex={0} aria-expanded={expanded} aria-controls={expanded ? detailsId : undefined}
                title="Vaqt tarixini ochish yoki yopish"
                onClick={() => setExpandedTask(current => current === key ? null : key)}
                onKeyDown={event => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setExpandedTask(current => current === key ? null : key);
                  }
                }}>
                <td className="p-3" style={{ position: "relative" }}>
                  {comparison && <span aria-hidden="true" style={{ position: "absolute", left: 0, top: 8, bottom: 8,
                    width: 3, borderRadius: 2, backgroundColor: `var(${comparison === "over" ? "--error" : "--success"})` }} />}
                  <span className="font-medium">{task.issue_key}</span><p className="mt-1 text-muted-foreground">{task.summary}</p>
                </td>
                {showAssigneeColumn && <td className="p-3">{task.assignee_name || "Biriktirilmagan"}</td>}
                <td className="p-3">{task.status_name || "Noma’lum"}<p className="mt-1 text-xs text-muted-foreground">{task.deleted ? "O‘chirilgan" : task.is_working ? "Vaqt yurmoqda" : "Vaqt to‘xtagan"}</p></td>
                <td className="p-3 whitespace-nowrap">{duration(task.assignee_seconds)}</td>
                <td className="p-3">{task.story_points == null ? "Belgilanmagan" : numberLabel(task.story_points)}</td>
                <td className="p-3 font-semibold tabular-nums" title={pointComparisonLabel}>
                  {timePoints === null ? "—" : numberLabel(timePoints)}
                  {pointComparisonLabel && <span className="sr-only"> · {pointComparisonLabel}</span>}
                </td>
              </tr>
              {expanded && <tr className="border-b"><td id={detailsId} colSpan={showAssigneeColumn ? 6 : 5} className="p-3">
                <TeamAnalyticsTaskDetails task={task} assigneeId={selectedId} showAll={assignee === "all"} timeZone={snapshot.timezone} />
              </td></tr>}
            </Fragment>;
          })}</tbody>
          <tfoot><tr className="border-t bg-muted/30 font-semibold">
            <td colSpan={showAssigneeColumn ? 3 : 2} />
            <td className="p-3 whitespace-nowrap">{duration(snapshot.summary.worked_seconds)}</td>
            <td className="p-3">{numberLabel(snapshot.summary.task_points)}</td>
            <td className="p-3">{validPoints ? numberLabel(snapshot.summary.work_days * pointsNumber) : "—"}</td>
          </tr></tfoot>
        </table></div>
        {snapshot.total > PAGE_SIZE && <div className="mt-4 flex gap-3">
          <Button disabled={offset === 0} onClick={() => { setExpandedTask(null); setOffset(value => Math.max(0, value - PAGE_SIZE)); }}>Oldingi</Button>
          <Button disabled={offset + snapshot.limit >= snapshot.total} onClick={() => { setExpandedTask(null); setOffset(value => value + PAGE_SIZE); }}>Keyingi</Button>
        </div>}
      </Card>}
      <Card>
        <h2 className="font-semibold">{isPersonSelected ? `${selectedPerson?.assignee_name || "Ijrochi"} natijasi` : "Jami hisob"}</h2>
        <p className="mt-3">{duration(snapshot.summary.worked_seconds)} ÷ {snapshot.daily_hours} soat = <strong>{numberLabel(snapshot.summary.work_days)} ish kuni</strong></p>
        {validPoints && <p className="mt-2">{numberLabel(snapshot.summary.work_days)} ish kuni × {numberLabel(pointsNumber)} point/kun = <strong>{numberLabel(snapshot.summary.work_days * pointsNumber)} pointga teng vaqt</strong></p>}
        {delay && <div className="mt-4 rounded-md border p-4">
          <h3 className="font-semibold">Tasklardan kechikish natijasi</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div><p className="text-sm text-muted-foreground">Normadan oshgan tasklar</p><p className="mt-1 font-semibold">{delay.count} ta</p></div>
            <div><p className="text-sm text-muted-foreground">Jami kechikish</p><p className="mt-1 font-semibold">{duration(delay.seconds)}</p><p className="text-sm text-muted-foreground">{numberLabel(delay.workDays)} ish kuni</p></div>
            <div><p className="text-sm text-muted-foreground">Ortiqcha sarflangan point</p><p className="mt-1 font-semibold">{numberLabel(delay.points)} point</p></div>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">Kechikish = ishlangan vaqt − (task pointi ÷ kunlik point × {snapshot.daily_hours} soat). Faqat normadan oshgan tasklar qo‘shiladi; tez tugagan tasklar kechikishni kamaytirmaydi. Bu Jira deadline’i bo‘yicha kechikish emas.</p>
          {snapshot.summary.missing_points > 0 && <p className="mt-2 text-sm text-muted-foreground">Pointi belgilanmagan {snapshot.summary.missing_points} ta task kechikish hisobiga kiritilmadi.</p>}
        </div>}
        {snapshot.summary.missing_points > 0 && <p className="mt-2 text-sm text-muted-foreground">{snapshot.summary.missing_points} ta taskda Jira pointi belgilanmagan.</p>}
        <p className="mt-3 text-sm text-muted-foreground">Task pointi — Jira bahosi. Vaqtga teng point — sarflangan vaqtning kiritilgan kunlik point bo‘yicha hisobi. Natija barcha sahifalarni qamrab oladi.</p>
      </Card>
    </>}
  </div>;
}
