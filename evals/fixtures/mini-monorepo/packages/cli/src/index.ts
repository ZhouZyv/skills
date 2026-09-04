#!/usr/bin/env node
import { dueTasks } from "@taskman/core";
import type { Task } from "@taskman/core";

const input = process.argv[2];
if (!input) {
  console.error("usage: taskman <tasks.json>");
  process.exit(1);
}

const tasks: Task[] = JSON.parse(input);
for (const task of dueTasks(tasks, new Date())) {
  console.log(`${task.priority}\t${task.title}`);
}
