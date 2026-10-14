"use client";
import { Clock3 } from "lucide-react";
import { Schedule, Frequency, weekdays, parseSchedule } from "@/lib/schedule";
import { Field } from "./common";
import { TimePicker } from "./time-picker";

export function SchedulePicker({
  value,
  onChange,
}: {
  value: Schedule;
  onChange: (value: Schedule) => void;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field
        label="重复频率"
        hint="选择任务的运行周期。"
        hintAriaHidden
      >
        <select
          value={value.frequency}
          onChange={(e) =>
            onChange({ ...value, frequency: e.target.value as Frequency })
          }
        >
          <option value="daily">每天</option>
          <option value="weekdays">工作日（周一至周五）</option>
          <option value="weekends">周末（周六、周日）</option>
          <option value="weekly">每周指定星期</option>
          <option value="monthly">每月指定日期</option>
          {parseSchedule(value.original).frequency === "custom" && (
            <option value="custom">保留原有计划</option>
          )}
        </select>
      </Field>
      {value.frequency === "custom" ? (
        <p className="self-center text-sm leading-6 text-muted">
          将保留原有执行计划。选择新的重复频率后，可重新设置执行时间。
        </p>
      ) : (
        <TimePicker
          value={value.time}
          onChange={(time) => onChange({ ...value, time })}
        />
      )}
      {value.frequency === "weekly" && (
        <fieldset className="sm:col-span-2">
          <legend className="mb-2 text-sm font-medium">执行星期</legend>
          <div className="flex flex-wrap gap-2">
            {weekdays.map((day) => (
              <label
                key={day.value}
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs"
              >
                <input
                  type="checkbox"
                  className="accent-emerald-600"
                  checked={value.weekdays.includes(day.value)}
                  onChange={(e) =>
                    onChange({
                      ...value,
                      weekdays: e.target.checked
                        ? [...value.weekdays, day.value]
                        : value.weekdays.filter((d) => d !== day.value),
                    })
                  }
                />
                {day.label}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {value.frequency === "monthly" && (
        <fieldset className="min-w-0 sm:col-span-2">
          <legend className="mb-2 text-sm font-medium">每月执行日期</legend>
          <p className="mb-3 text-xs leading-5 text-muted">
            可多选；每个所选日期均在同一时间执行。
          </p>
          <div className="grid max-w-md grid-cols-7 gap-2">
            {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
              <label key={day} className="relative cursor-pointer">
                <input
                  type="checkbox"
                  aria-label={`${day} 日`}
                  className="peer absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                  checked={value.monthDays.includes(day)}
                  onChange={(e) =>
                    onChange({
                      ...value,
                      monthDays: e.target.checked
                        ? [...value.monthDays, day]
                        : value.monthDays.filter((d) => d !== day),
                    })
                  }
                />
                <span className="flex h-10 items-center justify-center rounded-lg border border-line text-sm transition-colors hover:border-emerald-400 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white peer-focus-visible:ring-2 peer-focus-visible:ring-emerald-400 peer-focus-visible:ring-offset-2">
                  {day}
                </span>
              </label>
            ))}
          </div>
          {value.monthDays.some((day) => day > 28) && (
            <p className="mt-2 text-xs leading-5 text-muted">
              当月没有的日期会跳过，其余所选日期照常执行。
            </p>
          )}
        </fieldset>
      )}
      {value.frequency !== "custom" && (
        <p className="flex items-center gap-2 text-xs text-muted sm:col-span-2">
          <Clock3 size={13} />
          按所配置的时区执行；实际发送时间会加上随机延迟。
        </p>
      )}
    </div>
  );
}
