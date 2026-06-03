import { CheckCircle2 } from "lucide-react";

interface Step {
  label: string;
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: number;
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div role="list" aria-label="Progresso do formulário" className="flex items-center gap-2 mb-8">
      {steps.map((s, i) => (
        <div key={s.label} role="listitem" className="flex items-center gap-2">
          <div
            role="status"
            aria-current={i === currentStep ? "step" : undefined}
            aria-label={`${i < currentStep ? "Concluído: " : i === currentStep ? "Passo atual: " : "Pendente: "}${s.label}`}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              i === currentStep
                ? "bg-primary-500 text-white"
                : i < currentStep
                  ? "bg-success-500 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
            }`}
          >
            {i < currentStep ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <span aria-hidden="true">{i + 1}</span>}
            <span className="hidden sm:inline">{s.label}</span>
          </div>
          {i < steps.length - 1 && <div className="w-8 h-px bg-gray-300 dark:bg-gray-600" aria-hidden="true" />}
        </div>
      ))}
    </div>
  );
}
