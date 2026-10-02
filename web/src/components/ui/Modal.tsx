import type { ReactNode } from "react";
import { MotionModal, MotionModalBody, MotionModalHeader } from "../motion/MotionModal";

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  size?: "sm" | "md" | "lg";
}

export function Modal({ open, title, onClose, children, size = "md" }: ModalProps) {
  const titleId = `modal-title-${size}`;

  const width = {
    sm: "max-w-sm",
    md: "max-w-lg",
    lg: "max-w-2xl",
  }[size];

  return (
    <MotionModal open={open} onClose={onClose} labelledBy={titleId} panelClassName={width}>
      <MotionModalHeader title={title} titleId={titleId} onClose={onClose} />
      <MotionModalBody>{children}</MotionModalBody>
    </MotionModal>
  );
}
