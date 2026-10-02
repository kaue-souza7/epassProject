import { clsx } from "clsx";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={clsx(
        "epass-shimmer animate-pulse rounded-md bg-gray-200 dark:bg-gray-700",
        className,
      )}
    />
  );
}
