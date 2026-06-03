import { Skeleton } from "./Skeleton";
import { Card } from "./Card";

interface SkeletonDetailProps {
  fields?: number;
}

export function SkeletonDetail({ fields = 4 }: SkeletonDetailProps) {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <Skeleton className="h-5 w-32 mb-4" />
          <div className="space-y-4">
            {Array.from({ length: fields }).map((_, i) => (
              <div key={i}>
                <Skeleton className="h-3 w-16 mb-1" />
                <Skeleton className="h-4 w-40" />
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <Skeleton className="h-5 w-32 mb-4" />
          <div className="space-y-4">
            {Array.from({ length: fields }).map((_, i) => (
              <div key={i}>
                <Skeleton className="h-3 w-16 mb-1" />
                <Skeleton className="h-4 w-40" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
