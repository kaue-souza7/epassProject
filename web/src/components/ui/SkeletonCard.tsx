import { Skeleton } from "./Skeleton";

export function SkeletonCard() {
  return (
    <div className="bg-card dark:bg-card-dark rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="space-y-3">
        <Skeleton className="h-8 w-16 mx-auto" />
        <Skeleton className="h-4 w-24 mx-auto" />
      </div>
    </div>
  );
}

export function SkeletonDashboardCard() {
  return (
    <div className="bg-card dark:bg-card-dark rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="space-y-3">
        <Skeleton className="h-8 w-16 mx-auto" />
        <Skeleton className="h-4 w-28 mx-auto" />
      </div>
    </div>
  );
}
