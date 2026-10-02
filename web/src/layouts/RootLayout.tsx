import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Sidebar } from "../components/layout/Sidebar";
import { Header } from "../components/layout/Header";
import { PageTransition, RouteProgress } from "../components/motion";

export function RootLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const reduceMotion = useReducedMotion();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <RouteProgress />
        <main className="flex-1 overflow-auto p-4 md:p-6 bg-surface dark:bg-surface-dark relative">
          {!reduceMotion && (
            <motion.div
              key={location.pathname}
              className="pointer-events-none fixed inset-0 epass-aurora-bg"
              initial="hidden"
              animate="flash"
              variants={{ hidden: { opacity: 0 }, flash: { opacity: [0, 0.3, 0] } }}
              transition={{ duration: 0.9, times: [0, 0.3, 1] }}
              aria-hidden="true"
            />
          )}
          <div className="relative">
            <PageTransition>
              <Outlet />
            </PageTransition>
          </div>
        </main>
      </div>
    </div>
  );
}
