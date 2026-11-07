import { forwardRef } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, icon, className = "", id, ...rest },
  ref,
) {
  const inputId = id ?? rest.name ?? label.toLowerCase().replace(/\s+/g, "-");
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      <label
        htmlFor={inputId}
        className="block text-[13px] font-medium text-[#C7D0DC]"
      >
        {label}
      </label>
      <div
        className={[
          "flex items-center gap-2 rounded-xl border bg-ink/70 px-3.5",
          "transition-colors focus-within:border-mint/60 focus-within:bg-ink",
          error ? "border-red-500/50" : "border-white/10",
        ].join(" ")}
      >
        {icon ? <span className="text-mist">{icon}</span> : null}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
          className={[
            "h-11 w-full bg-transparent text-sm text-[#F5F7FA]",
            "placeholder:text-mist/60 focus:outline-none",
            className,
          ].join(" ")}
          {...rest}
        />
      </div>
      {error ? (
        <p id={`${inputId}-error`} role="alert" className="text-xs text-red-300">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="text-xs text-mist">
          {hint}
        </p>
      ) : null}
    </div>
  );
});
