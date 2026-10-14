"use client";
import { useId } from "react";
import * as Popover from "@radix-ui/react-popover";
import { Clock3 } from "lucide-react";
import { Button } from "./ui/button";

const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
const minutes = Array.from({ length: 60 }, (_, i) =>
  String(i).padStart(2, "0"),
);

export function TimePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const id = useId();
  const [hour, minute] = /^([01]\d|2[0-3]):[0-5]\d$/.test(value)
    ? value.split(":")
    : ["00", "00"];

  return (
    <div className="grid content-start gap-2 text-sm font-medium text-ink">
      <label htmlFor={id}>执行时间</label>
      <Popover.Root>
        <Popover.Anchor asChild>
          <div className="relative">
            <input
              id={id}
              aria-describedby={`${id}-hint`}
              className="time-input pr-12"
              type="time"
              step="60"
              required
              value={value}
              onChange={(e) => onChange(e.target.value)}
            />
            <Popover.Trigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="选择执行时间"
                title="选择执行时间"
                className="absolute right-1 top-1/2 -translate-y-1/2"
              >
                <Clock3 size={18} aria-hidden="true" />
              </Button>
            </Popover.Trigger>
          </div>
        </Popover.Anchor>
        <Popover.Portal>
          <Popover.Content
            aria-label="选择执行时间"
            align="end"
            sideOffset={8}
            collisionPadding={16}
            className="z-[60] w-56 rounded-xl border border-line bg-white p-3 shadow-lg focus:outline-none"
          >
            <div className="grid grid-cols-2 gap-3">
              <label className="grid gap-2 text-center text-xs font-medium text-muted">
                小时
                <select
                  size={5}
                  value={hour}
                  onChange={(e) => onChange(`${e.target.value}:${minute}`)}
                  className="h-40 px-1 py-1 text-center tabular-nums"
                >
                  {hours.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-2 text-center text-xs font-medium text-muted">
                分钟
                <select
                  size={5}
                  value={minute}
                  onChange={(e) => onChange(`${hour}:${e.target.value}`)}
                  className="h-40 px-1 py-1 text-center tabular-nums"
                >
                  {minutes.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <Popover.Close asChild>
              <Button
                type="button"
                size="sm"
                className="mt-3 w-full"
                onClick={() => onChange(`${hour}:${minute}`)}
              >
                完成
              </Button>
            </Popover.Close>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
      <span
        id={`${id}-hint`}
        className="text-xs font-normal leading-5 text-muted"
      >
        点击时钟选择，或用键盘输入，例如 08:30。
      </span>
    </div>
  );
}
