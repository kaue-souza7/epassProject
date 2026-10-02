import type { ReactNode } from "react";
import { clsx } from "clsx";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { SkeletonTable } from "./SkeletonTable";
import { tBase, tFast } from "../motion/transitions";

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
  const reduceMotion = useReducedMotion();

  const shell =
    "bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden";

  return (
    <AnimatePresence mode="wait" initial={false}>
      {loading ? (
        <motion.div
          key="loading"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: tFast }}
          transition={tBase}
        >
          <SkeletonTable rows={5} columns={columns.length} />
        </motion.div>
      ) : data.length === 0 ? (
        <motion.div
          key="empty"
          className={clsx(shell, "p-12 text-center")}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, transition: tFast }}
          transition={tBase}
        >
          <p className="text-gray-400 dark:text-gray-500 text-lg">{emptyMessage}</p>
        </motion.div>
      ) : (
        <motion.div
          key="table"
          className={shell}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, transition: tFast }}
          transition={tBase}
        >
          <div className="overflow-x-auto epass-scrollbar">
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
              <motion.tbody
                className="divide-y divide-gray-200 dark:divide-gray-700"
                initial="hidden"
                animate="visible"
                variants={{
                  hidden: {},
                  visible: reduceMotion
                    ? {}
                    : { transition: { staggerChildren: 0.035 } },
                }}
              >
                {data.map((item) => (
                  <motion.tr
                    key={keyExtractor(item)}
                    onClick={() => onRowClick?.(item)}
                    variants={{
                      hidden: { opacity: 0, y: 8 },
                      visible: { opacity: 1, y: 0 },
                    }}
                    transition={tBase}
                    className={clsx(
                      "transition-colors",
                      onRowClick && "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/30",
                    )}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={clsx(
                          "px-4 py-3 text-sm text-gray-700 dark:text-gray-300",
                          col.className,
                        )}
                      >
                        {col.render ? col.render(item) : (item as any)[col.key] ?? "—"}
                      </td>
                    ))}
                  </motion.tr>
                ))}
              </motion.tbody>
            </table>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
