import { SkeletonDashboardCard } from "./SkeletonCard";
import { SkeletonDashboardSection } from "./SkeletonDashboardSection";

export function SkeletonDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <SkeletonDashboardSection />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonDashboardCard key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonDashboardSection />
        <SkeletonDashboardSection />
      </div>
    </div>
  );
}
