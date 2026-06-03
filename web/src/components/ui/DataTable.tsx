import type { ReactNode } from "react";
import { clsx } from "clsx";
import { SkeletonTable } from "./SkeletonTable";

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  loading,
  emptyMessage = "Nenhum registro encontrado",
  onRowClick,
}: DataTableProps<T>) {
  if (loading) {
    return <SkeletonTable rows={5} columns={columns.length} />;
  }

  if (data.length === 0) {
    return (
      <div className="bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 p-12 text-center">
        <p className="text-gray-400 dark:text-gray-500 text-lg">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={clsx(
                    "px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider",
                    col.className,
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {data.map((item) => (
              <tr
                key={keyExtractor(item)}
                onClick={() => onRowClick?.(item)}
                className={clsx(
                  "transition-colors",
                  onRowClick && "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/30",
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx("px-4 py-3 text-sm text-gray-700 dark:text-gray-300", col.className)}>
                    {col.render ? col.render(item) : (item as any)[col.key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
