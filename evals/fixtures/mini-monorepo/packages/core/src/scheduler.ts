import type { Task, TaskFilter } from "./index.js";
import { DEFAULT_FILTER } from "./index.js";
import { sendNotification } from "@taskman/notify";

const PRIORITY_WEIGHT = { high: 0, normal: 1, low: 2 } as const;

export function dueTasks(tasks: Task[], now: Date, filter: TaskFilter = DEFAULT_FILTER): Task[] {
  return tasks
    .filter((t) => t.dueAt <= now || filter.includeOverdue)
    .sort((a, b) => PRIORITY_WEIGHT[a.priority] - PRIORITY_WEIGHT[b.priority]);
}

export async function remindDue(tasks: Task[], now: Date): Promise<number> {
  const due = dueTasks(tasks, now);
  for (const task of due) {
    await sendNotification("email", { subject: `到期提醒：${task.title}` });
  }
  return due.length;
}
