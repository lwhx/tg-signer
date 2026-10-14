"use client";
import * as SwitchPrimitive from "@radix-ui/react-switch";
export function Switch({
  checked,
  onCheckedChange,
  disabled,
  label,
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <SwitchPrimitive.Root
      aria-label={label}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      className="inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full bg-slate-200 transition-colors data-[state=checked]:bg-primary disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-emerald-400"
    >
      <SwitchPrimitive.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-[18px]" />
    </SwitchPrimitive.Root>
  );
}
