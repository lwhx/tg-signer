export type Frequency =
  | "daily"
  | "weekdays"
  | "weekends"
  | "weekly"
  | "monthly"
  | "custom";
export interface Schedule {
  frequency: Frequency;
  time: string;
  weekdays: number[];
  monthDays: number[];
  original: string;
}
export const weekdays = [
  { value: 1, label: "周一" },
  { value: 2, label: "周二" },
  { value: 3, label: "周三" },
  { value: 4, label: "周四" },
  { value: 5, label: "周五" },
  { value: 6, label: "周六" },
  { value: 0, label: "周日" },
];

export function parseSchedule(cron: string): Schedule {
  const schedule: Schedule = {
    frequency: "custom",
    time: "08:00",
    weekdays: [1],
    monthDays: [1],
    original: cron,
  };
  const parts = cron.trim().split(/\s+/);
  if (parts.length !== 5) return schedule;
  const [minute, hour, day, month, week] = parts;
  if (
    !/^\d+$/.test(minute) ||
    !/^\d+$/.test(hour) ||
    Number(minute) > 59 ||
    Number(hour) > 23 ||
    month !== "*"
  )
    return schedule;
  schedule.time = `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
  if (week === "*" && /^\d+(,\d+)*$/.test(day)) {
    const monthDays = [...new Set(day.split(",").map(Number))].sort(
      (a, b) => a - b,
    );
    if (monthDays.every((d) => d >= 1 && d <= 31)) {
      return { ...schedule, frequency: "monthly", monthDays };
    }
  }
  if (day !== "*") return schedule;
  if (week === "*") return { ...schedule, frequency: "daily" };
  const selected = new Set<number>();
  for (const part of week.split(",")) {
    const range = part.match(/^(\d)(?:-(\d))?$/);
    if (!range) return schedule;
    const start = Number(range[1]),
      end = Number(range[2] ?? range[1]);
    if (start > 7 || end > 7 || start > end) return schedule;
    for (let i = start; i <= end; i++) selected.add(i % 7);
  }
  schedule.weekdays = weekdays
    .filter((d) => selected.has(d.value))
    .map((d) => d.value);
  if (!selected.size) return schedule;
  schedule.frequency =
    selected.size === 7
      ? "daily"
      : selected.size === 5 && [1, 2, 3, 4, 5].every((d) => selected.has(d))
        ? "weekdays"
        : selected.size === 2 && selected.has(0) && selected.has(6)
          ? "weekends"
          : "weekly";
  return schedule;
}

export function scheduleCron(schedule: Schedule): string {
  if (schedule.frequency === "custom") return schedule.original;
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(schedule.time))
    throw new Error("请选择或输入有效的执行时间（例如 08:30）");
  const [hour, minute] = schedule.time.split(":").map(Number);
  if (schedule.frequency === "monthly") {
    const monthDays = [...new Set(schedule.monthDays)].sort((a, b) => a - b);
    if (!monthDays.length) throw new Error("请至少选择一个每月执行日期");
    if (monthDays.some((day) => !Number.isInteger(day) || day < 1 || day > 31))
      throw new Error("请选择有效的每月执行日期（1–31 日）");
    return `${minute} ${hour} ${monthDays.join(",")} * *`;
  }
  let week = "*";
  if (schedule.frequency === "weekdays") week = "1-5";
  else if (schedule.frequency === "weekends") week = "0,6";
  else if (schedule.frequency === "weekly") {
    const selected = weekdays.filter((d) =>
      schedule.weekdays.includes(d.value),
    );
    if (!selected.length) throw new Error("请至少选择一个执行星期");
    week = selected.map((d) => d.value).join(",");
  }
  return `${minute} ${hour} * * ${week}`;
}

export function describeSchedule(cron: string): string {
  const schedule = parseSchedule(cron);
  const labels = {
    daily: "每天",
    weekdays: "工作日",
    weekends: "周末",
    weekly: weekdays
      .filter((d) => schedule.weekdays.includes(d.value))
      .map((d) => d.label)
      .join("、"),
    monthly: `每月 ${schedule.monthDays.join("、")} 日`,
    custom: "已导入的自定义计划",
  };
  return schedule.frequency === "custom"
    ? labels.custom
    : `${labels[schedule.frequency]} ${schedule.time}`;
}
