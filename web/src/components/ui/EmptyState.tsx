import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icon className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
      <p className="text-base font-medium text-gray-500 dark:text-gray-400">
        {title}
      </p>
      {description && (
        <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
          {description}
        </p>
      )}
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-4 text-sm font-medium text-primary-500 hover:text-primary-600 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
