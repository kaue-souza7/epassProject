import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { clsx } from "clsx";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from "lucide-react";
import { toastVariants } from "../motion/transitions";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextType {
  toast: (type: ToastType, message: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

let nextId = 0;

const DURATION = 4000;

const TONE: Record<ToastType, { className: string; icon: ReactNode }> = {
  success: {
    className: "bg-success-500 text-white",
    icon: <CheckCircle className="h-5 w-5 flex-shrink-0" />,
  },
  error: {
    className: "bg-danger-500 text-white",
    icon: <AlertCircle className="h-5 w-5 flex-shrink-0" />,
  },
  info: {
    className: "bg-primary-500 text-white",
    icon: <Info className="h-5 w-5 flex-shrink-0" />,
  },
  warning: {
    className: "bg-warning-500 text-white",
    icon: <AlertTriangle className="h-5 w-5 flex-shrink-0" />,
  },
};

function ToastCard({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: number) => void;
}) {
  const reduceMotion = useReducedMotion();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    timer.current = setTimeout(() => onDismiss(toast.id), DURATION);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [toast.id, onDismiss]);

  const tone = TONE[toast.type];

  return (
    <motion.div
      layout
      variants={toastVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      drag={reduceMotion ? false : "x"}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.6}
      onDragEnd={(_, info) => {
        if (Math.abs(info.offset.x) > 90) onDismiss(toast.id);
      }}
      role="status"
      aria-live="polite"
      className={clsx(
        "group relative flex items-center gap-3 px-4 py-3 rounded-xl shadow-epass-lg text-sm font-medium overflow-hidden cursor-grab active:cursor-grabbing",
        tone.className,
      )}
    >
      <motion.span
        className="absolute inset-x-0 bottom-0 h-[3px] bg-white/40 origin-left"
        initial={{ scaleX: 1 }}
        animate={{ scaleX: 0 }}
        transition={{ duration: DURATION / 1000, ease: "linear" }}
      />
      <span className="relative">{tone.icon}</span>
      <span className="relative flex-1 min-w-0">{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Fechar notificação"
        className="relative flex-shrink-0 opacity-70 hover:opacity-100 transition-opacity"
      >
        <X className="h-4 w-4 ml-2" />
      </button>
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((type: ToastType, message: string) => {
    const id = nextId++;
    setToasts((prev) => [...prev.slice(-3), { id, type, message }]);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] w-[calc(100%-2rem)] max-w-sm space-y-2 md:left-auto md:right-4 md:translate-x-0 md:w-auto">
        <AnimatePresence mode="popLayout" initial={false}>
          {toasts.map((t) => (
            <ToastCard key={t.id} toast={t} onDismiss={dismiss} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
