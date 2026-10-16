import { summarizeTasks } from "./team-analytics-calculations";
import { applyTaskWorkLimits } from "./team-analytics-limits";
import type { AnalyticsSnapshot, AnalyticsSprint, AnalyticsTask } from "@/lib/team-analytics-types";

/** Browser-only fixtures: never sent to Jira or persisted to the database. */
export function createAnalyticsDemo(workingStatus: string, dailyHours = 8, weeklyHours = 40): AnalyticsSnapshot {
  const now = Date.now();
  const fortnight = 14 * 86400_000;
  const sprints: AnalyticsSprint[] = Array.from({ length: 9 }, (_, index) => ({
    jira_source: "demo", id: 23 - index, name: `Sprint ${23 - index}`, state: index === 0 ? "active" : "closed",
    started_at: new Date(now - (index + 1) * fortnight).toISOString(),
    ends_at: new Date(index === 0 ? now + fortnight : now - index * fortnight).toISOString(),
    ...(index > 0 ? { completed_at: new Date(now - index * fortnight).toISOString() } : {}),
  }));
  const samples = [
    { key: "DEMO-101", name: "Ali Valiyev", summary: "Login sahifasini tayyorlash", status: workingStatus, hours: [3, 2], active: true },
    { key: "DEMO-102", name: "Vali Karimov", summary: "To‘lov API integratsiyasi", status: "Timeout", hours: [2.5], active: false },
    { key: "DEMO-103", name: "Lola Ahmedova", summary: "Test case eksporti", status: "Done", hours: [4, 4, 4, 4], active: false },
    { key: "DEMO-104", name: "Ali Valiyev", summary: "Webhook xatolarini tekshirish", status: "Review", hours: [1.5], active: false },
    { key: "DEMO-105", name: "Sardor Olimov", summary: "Dashboard filtrlari", status: workingStatus, hours: [1.25], active: true },
    { key: "DEMO-106", name: "Lola Ahmedova", summary: "Retest: eksport formatini tuzatish", status: "Retest", hours: [2, 0.5], active: false },
    { key: "DEMO-107", name: "Vali Karimov", summary: "Profil validatsiyasi", status: "Rejected", hours: [0.75], active: false },
    { key: "DEMO-108", name: "", summary: "Bildirishnoma dizayni", status: "To Do", hours: [], active: false },
    { key: "DEMO-109", name: "Ali Valiyev", summary: "Profil sahifasini tayyorlash", status: "Done", hours: [4, 4], active: false },
    { key: "DEMO-110", name: "Ali Valiyev", summary: "Task ro‘yxatini filtrlash", status: "Review", hours: [3, 3], active: false },
    { key: "DEMO-111", name: "Ali Valiyev", summary: "Hisobot eksportini qo‘shish", status: "Done", hours: [4, 4, 4], active: false },
    { key: "DEMO-112", name: "Ali Valiyev", summary: "Forma xatolarini ko‘rsatish", status: "Review", hours: [1], active: false },
    { key: "DEMO-113", name: "Ali Valiyev", summary: "API javoblarini optimallashtirish", status: "Timeout", hours: [4, 3], active: false },
    { key: "DEMO-114", name: "Ali Valiyev", summary: "Mobil jadval ko‘rinishini tuzatish", status: "Retest", hours: [0.5, 1.5], active: false },
    { key: "DEMO-115", name: "Ali Valiyev", summary: "Integratsiya holatini ko‘rsatish", status: "Done", hours: [4, 4, 2], active: false },
    { key: "DEMO-116", name: "Ali Valiyev", summary: "Bildirishnoma sozlamalarini qo‘shish", status: "To Do", hours: [], active: false },
    { key: "DEMO-117", name: "Ali Valiyev", summary: "Kechikkan task: login sessiyasini tuzatish", status: "Done", hours: [4, 4, 2], active: false },
    { key: "DEMO-118", name: "Ali Valiyev", summary: "Kechikkan task: to‘lov xatolarini tuzatish", status: "Review", hours: [4, 4, 4, 4, 2], active: false },
    { key: "DEMO-119", name: "Ali Valiyev", summary: "Kechikkan task: hisobot generatsiyasi", status: "Done", hours: [4, 4, 4, 4, 4, 4, 2], active: false },
  ];
  const rawTasks: AnalyticsTask[] = samples.map((sample, index) => {
    const assigneeId = sample.name ? `demo-${sample.name.split(" ")[0].toLowerCase()}` : "";
    const intervals = sample.hours.map((hours, intervalIndex) => {
      // Past tasks use distinct business days and morning/afternoon work sessions.
      const endDate = new Date(now);
      const daysBack = sample.active ? sample.hours.length - intervalIndex - 1
        : (index + 1) * 4 + Math.floor((sample.hours.length - 1) / 2) - Math.floor(intervalIndex / 2);
      let remaining = daysBack;
      while (remaining > 0) {
        endDate.setDate(endDate.getDate() - 1);
        if (endDate.getDay() !== 0 && endDate.getDay() !== 6) remaining -= 1;
      }
      if (!sample.active || intervalIndex !== sample.hours.length - 1) {
        endDate.setHours(intervalIndex % 2 === 0 ? 13 : 18, 0, 0, 0);
      }
      const end = endDate.getTime();
      return { started_at: new Date(end - hours * 3600_000).toISOString(), ended_at: new Date(end).toISOString(),
        seconds: hours * 3600, assignee_id: assigneeId, assignee_name: sample.name, working_status: workingStatus, is_open: sample.active && intervalIndex === sample.hours.length - 1 };
    });
    const sprintIds = intervals.length ? sprints.filter(sprint => intervals.some(interval =>
      Date.parse(interval.ended_at) > Date.parse(sprint.started_at!) &&
      Date.parse(interval.started_at) < Date.parse(sprint.completed_at || sprint.ends_at!))).map(sprint => sprint.id) : [23];
    return { jira_source: "demo", issue_id: String(index + 1), issue_key: sample.key, summary: sample.summary, sprint_ids: sprintIds,
      status_name: sample.status, assignee_id: assigneeId, assignee_name: sample.name,
      story_points: [2, 2, 4, 2, 2, 2, 2, 2, 4, 2, 4, 2, 2, 2, 4, 2, 2, 4, 6][index], assignee_seconds: intervals.reduce((sum, interval) => sum + interval.seconds, 0), work_days: intervals.reduce((sum, interval) => sum + interval.seconds, 0) / (dailyHours * 3600),
      is_working: sample.active, deleted: false, total_seconds: intervals.reduce((sum, interval) => sum + interval.seconds, 0), intervals };
  });
  const tasks = applyTaskWorkLimits(rawTasks, dailyHours, weeklyHours);
  const assignees = Array.from(new Map(tasks.filter(task => task.assignee_id).map(task => [task.assignee_id,
    { jira_source: task.jira_source, assignee_id: task.assignee_id!, assignee_name: task.assignee_name! }])).values())
    .sort((a, b) => a.assignee_name.localeCompare(b.assignee_name));
  return { assignees, sprints, selected_sprint: null, sprint_window: null, daily_hours: dailyHours, weekly_hours: weeklyHours,
    summary: summarizeTasks(tasks),
    timezone: "Asia/Tashkent",
    working_status: workingStatus, tasks, total: tasks.length, limit: 100, offset: 0, generated_at: new Date(now).toISOString() };
}
