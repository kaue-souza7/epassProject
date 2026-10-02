import { Button } from "./Button";
import { MotionModal } from "../motion/MotionModal";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  variant = "danger",
  loading,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <MotionModal
      open={open}
      onClose={onCancel}
      labelledBy="confirm-dialog-title"
      panelClassName="max-w-sm p-6"
    >
      <div className="relative">
        <h3
          id="confirm-dialog-title"
          className="text-lg font-semibold text-gray-900 dark:text-gray-100"
        >
          {title}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">{message}</p>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="ghost" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button variant={variant} onClick={onConfirm} loading={loading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </MotionModal>
  );
}
