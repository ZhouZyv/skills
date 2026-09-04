import { describe, expect, it } from "vitest";
import { dueTasks } from "../src/scheduler.js";
import type { Task } from "../src/index.js";

const t = (id: string, priority: Task["priority"], dueAt: Date): Task => ({
  id,
  title: id,
  dueAt,
  priority,
});

describe("dueTasks", () => {
  it("sorts by priority weight", () => {
    const now = new Date("2026-01-01T00:00:00Z");
    const tasks = [
      t("a", "low", now),
      t("b", "high", now),
      t("c", "normal", now),
    ];
    expect(dueTasks(tasks, now).map((x) => x.id)).toEqual(["b", "c", "a"]);
  });
});
