export interface Task {
  id: string;
  title: string;
  dueAt: Date;
  priority: "low" | "normal" | "high";
}

export type TaskFilter = {
  includeOverdue: boolean;
};

export const DEFAULT_FILTER: TaskFilter = {
  includeOverdue: true,
};
