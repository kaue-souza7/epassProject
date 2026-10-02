import { clsx } from "clsx";
import { motion, useReducedMotion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { springSoft } from "../motion/transitions";

interface Step {
  label: string;
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: number;
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  const reduceMotion = useReducedMotion();
  const pct =
    steps.length > 1 ? (currentStep / (steps.length - 1)) * 100 : 0;

  return (
    <div className="mb-8">
      <div
        role="list"
        aria-label="Progresso do formulário"
        className="flex items-center gap-2"
      >
        {steps.map((s, i) => (
          <div key={s.label} role="listitem" className="flex items-center gap-2">
            <motion.div
              role="status"
              aria-current={i === currentStep ? "step" : undefined}
              aria-label={`${i < currentStep ? "Concluído: " : i === currentStep ? "Passo atual: " : "Pendente: "}${s.label}`}
              className={clsx(
                "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
                i === currentStep && "shadow-epass-primary",
                i === currentStep
                  ? "bg-primary-500 text-white"
                  : i < currentStep
                    ? "bg-success-500 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400",
              )}
              initial={false}
              animate={
                reduceMotion
                  ? undefined
                  : { scale: i === currentStep ? 1 : 0.96 }
              }
              transition={springSoft}
            >
              {i < currentStep ? (
                <motion.span
                  initial={reduceMotion ? undefined : { scale: 0, rotate: -90 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={springSoft}
                >
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                </motion.span>
              ) : (
                <span aria-hidden="true">{i + 1}</span>
              )}
              <span className="hidden sm:inline">{s.label}</span>
            </motion.div>
            {i < steps.length - 1 && (
              <div
                className="relative w-8 h-1 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden"
                aria-hidden="true"
              >
                <motion.div
                  className="absolute inset-0 origin-left rounded-full bg-success-500"
                  initial={reduceMotion ? false : { scaleX: 0 }}
                  animate={{ scaleX: i < currentStep ? 1 : 0 }}
                  transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      <div
        className="h-1 mt-3 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden"
        aria-hidden="true"
      >
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-500"
          initial={reduceMotion ? false : { scaleX: 0 }}
          animate={{ scaleX: pct / 100 }}
          transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
          style={{ originX: 0 }}
        />
      </div>
    </div>
  );
}
