import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { clsx } from "clsx";
import { backdropVariants, dialogVariants } from "./transitions";

let scrollLocks = 0;

function useBodyScrollLock(active: boolean) {
  useEffect(() => {
    if (!active) return;
    scrollLocks += 1;
    document.body.style.overflow = "hidden";
    return () => {
      scrollLocks -= 1;
      if (scrollLocks <= 0) {
        scrollLocks = 0;
        document.body.style.overflow = "";
      }
    };
  }, [active]);
}

export function usePresence(open: boolean) {
  const [mounted, setMounted] = useState(open);

  useEffect(() => {
    if (open) setMounted(true);
  }, [open]);

  return mounted;
}

interface MotionModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  labelledBy?: string;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
  className?: string;
  panelClassName?: string;
}

export function MotionModal({
  open,
  onClose,
  children,
  labelledBy,
  closeOnBackdrop = true,
  closeOnEscape = true,
  className,
  panelClassName,
}: MotionModalProps) {
  const mounted = usePresence(open);
  useBodyScrollLock(mounted);

  useEffect(() => {
    if (!mounted || !closeOnEscape) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mounted, closeOnEscape, onClose]);

  return (
    <AnimatePresence>
      {mounted && (
        <div
          className={clsx(
            "fixed inset-0 z-50 flex items-center justify-center",
            className,
          )}
        >
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute inset-0 bg-black/50 backdrop-blur-[3px]"
            onClick={closeOnBackdrop ? onClose : undefined}
          />

          <motion.div
            variants={dialogVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            className={clsx(
              "relative bg-card dark:bg-card-dark rounded-2xl shadow-epass-xl w-full mx-4 border border-gray-200 dark:border-gray-700 flex flex-col max-h-[85vh] overflow-hidden",
              panelClassName,
            )}
          >
            <div className="pointer-events-none absolute inset-x-0 top-0 h-28 epass-aurora-bg opacity-60 dark:opacity-25" />
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

interface MotionModalHeaderProps {
  title: string;
  titleId?: string;
  onClose: () => void;
  children?: ReactNode;
}

export function MotionModalHeader({
  title,
  titleId,
  onClose,
  children,
}: MotionModalHeaderProps) {
  return (
    <div className="relative flex items-center justify-between gap-4 p-6 pb-4 border-b border-gray-200 dark:border-gray-700">
      <h3
        id={titleId}
        className="text-lg font-semibold text-gray-900 dark:text-gray-100"
      >
        {title}
      </h3>
      <div className="flex items-center gap-2">
        {children}
        <button
          onClick={onClose}
          aria-label="Fechar"
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

export function MotionModalBody({ children }: { children: ReactNode }) {
  return (
    <div className="relative p-6 pt-4 overflow-y-auto">{children}</div>
  );
}
