import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Erro ao carregar dados",
  message = "Não foi possível carregar as informações. Tente novamente.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center" role="alert">
      <AlertCircle className="h-12 w-12 text-danger-500 mb-4" />
      <p className="text-base font-semibold text-gray-900 dark:text-gray-100">
        {title}
      </p>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-md">
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-500 border border-primary-500 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Tentar novamente
        </button>
      )}
    </div>
  );
}
