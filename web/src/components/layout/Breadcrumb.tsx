import { Link } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

interface Crumb {
  label: string;
  path?: string;
}

interface BreadcrumbProps {
  items: Crumb[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 min-w-0 overflow-hidden">
      <Link to="/" className="hover:text-primary-500 transition-colors flex-shrink-0">
        <Home className="h-4 w-4" />
      </Link>
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1 min-w-0">
          <ChevronRight className="h-4 w-4 flex-shrink-0" />
          {item.path ? (
            <Link to={item.path} className="hover:text-primary-500 transition-colors truncate">
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-900 dark:text-gray-100 font-medium truncate">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
