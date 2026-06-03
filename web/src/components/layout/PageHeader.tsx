import type { ReactNode } from "react";
import { Plus } from "lucide-react";
import { Button } from "../ui/Button";

interface PageHeaderProps {
  title: string;
  description?: string;
  children?: ReactNode;
  onNew?: () => void;
  newLabel?: string;
  showNew?: boolean;
}

export function PageHeader({ title, description, children, onNew, newLabel = "Novo", showNew = true }: PageHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
      <div className="min-w-0">
        <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 truncate">{title}</h1>
        {description && <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate">{description}</p>}
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        {children}
        {showNew && onNew && (
          <Button onClick={onNew}>
            <Plus className="h-4 w-4 mr-2" />
            {newLabel}
          </Button>
        )}
      </div>
    </div>
  );
}
