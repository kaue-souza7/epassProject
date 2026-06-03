import { forwardRef, type SelectHTMLAttributes } from "react";
import { clsx } from "clsx";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, placeholder, className, id, ...props }, ref) => {
  const selectId = id || label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="relative">
      <select
        ref={ref}
        id={selectId}
        className={clsx(
          "peer w-full px-3 pt-5 pb-2 text-sm bg-transparent border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-0 appearance-none",
          error
            ? "border-danger-500 focus:ring-danger-500"
            : "border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500",
          "dark:text-gray-100",
          className,
        )}
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <label
        htmlFor={selectId}
        className={clsx(
          "absolute left-3 top-1 text-xs transition-all peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-sm peer-placeholder-shown:text-gray-400 peer-focus:top-1 peer-focus:text-xs peer-focus:text-primary-500",
          error ? "text-danger-500" : "text-gray-500 dark:text-gray-400",
        )}
      >
        {label}
      </label>
      <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
      {error && <p className="mt-1 text-xs text-danger-500">{error}</p>}
    </div>
  );
  },
);
