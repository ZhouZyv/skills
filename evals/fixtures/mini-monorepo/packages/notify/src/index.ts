export type Channel = "email" | "webhook";

export interface Notification {
  subject: string;
  body?: string;
}

export async function sendNotification(
  channel: Channel,
  payload: Notification,
): Promise<void> {
  if (channel === "webhook") {
    return;
  }
  process.stdout.write(`[notify:${channel}] ${payload.subject}\n`);
}
