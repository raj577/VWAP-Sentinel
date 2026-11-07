"use client";

import { useState } from "react";

import { Eye, EyeOff, Lock } from "@/components/ui/icons";

interface PasswordInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function PasswordInput({
  label = "Password",
  error,
  hint,
  id = "password",
  className = "",
  ...rest
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-[13px] font-medium text-[#C7D0DC]">
        {label}
      </label>
      <div
        className={[
          "flex items-center gap-2 rounded-xl border bg-ink/70 px-3.5",
          "transition-colors focus-within:border-mint/60 focus-within:bg-ink",
          error ? "border-red-500/50" : "border-white/10",
        ].join(" ")}
      >
        <span className="text-mist">
          <Lock size={16} />
        </span>
        <input
          id={id}
          type={visible ? "text" : "password"}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={[
            "h-11 w-full bg-transparent text-sm text-[#F5F7FA]",
            "placeholder:text-mist/60 focus:outline-none",
            className,
          ].join(" ")}
          {...rest}
        />
        <button
          type="button"
          onClick={() => setVisible((value) => !value)}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          className="rounded p-1 text-mist transition-colors hover:text-[#F5F7FA] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mint/60"
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs text-red-300">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-mist">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
