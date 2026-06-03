import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { clsx } from "clsx";
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from "lucide-react";

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

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((type: ToastType, message: string) => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] w-[calc(100%-2rem)] max-w-sm space-y-2 md:left-auto md:right-4 md:translate-x-0 md:w-auto">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={clsx(
              "flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium animate-in slide-in-from-top",
              {
                "bg-success-500 text-white": t.type === "success",
                "bg-danger-500 text-white": t.type === "error",
                "bg-primary-500 text-white": t.type === "info",
                "bg-warning-500 text-white": t.type === "warning",
              },
            )}
          >
            {t.type === "success" && <CheckCircle className="h-5 w-5 flex-shrink-0" />}
            {t.type === "error" && <AlertCircle className="h-5 w-5 flex-shrink-0" />}
            {t.type === "info" && <Info className="h-5 w-5 flex-shrink-0" />}
            {t.type === "warning" && <AlertTriangle className="h-5 w-5 flex-shrink-0" />}
            <span className="flex-1 min-w-0">{t.message}</span>
            <button onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))} className="flex-shrink-0">
              <X className="h-4 w-4 ml-2" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
