import type { Transition, Variants } from "framer-motion";

export const EASE_EPASS = [0.16, 1, 0.3, 1] as const;
export const EASE_IN_OUT = [0.65, 0, 0.35, 1] as const;

export const springSoft: Transition = {
  type: "spring",
  stiffness: 320,
  damping: 32,
  mass: 0.8,
};

export const springPop: Transition = {
  type: "spring",
  stiffness: 420,
  damping: 24,
  mass: 0.6,
};

export const tFast: Transition = { duration: 0.2, ease: EASE_EPASS };
export const tBase: Transition = { duration: 0.35, ease: EASE_EPASS };
export const tSlow: Transition = { duration: 0.55, ease: EASE_EPASS };

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: tFast },
  exit: { opacity: 0, transition: tFast },
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: tBase },
  exit: { opacity: 0, y: -8, transition: tFast },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.94 },
  visible: { opacity: 1, scale: 1, transition: springSoft },
  exit: { opacity: 0, scale: 0.96, transition: tFast },
};

export const listContainer: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.045, delayChildren: 0.04 },
  },
};

export const listItem: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: tBase },
  exit: { opacity: 0, y: -6, transition: tFast },
};

export const gridContainer: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
  },
};

export const pageVariants: Variants = {
  initial: { opacity: 0, y: 16, scale: 0.988 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.42, ease: EASE_EPASS },
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.995,
    transition: { duration: 0.2, ease: EASE_IN_OUT },
  },
};

export const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.22 } },
  exit: { opacity: 0, transition: { duration: 0.18 } },
};

export const dialogVariants: Variants = {
  hidden: { opacity: 0, scale: 0.92, y: 18 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springPop,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 10,
    transition: tFast,
  },
};

export const toastVariants: Variants = {
  hidden: { opacity: 0, y: -24, scale: 0.9 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: springPop,
  },
  exit: {
    opacity: 0,
    x: 48,
    scale: 0.9,
    transition: tFast,
  },
};

export const dropdownVariants: Variants = {
  hidden: { opacity: 0, y: -8, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: tBase,
  },
  exit: {
    opacity: 0,
    y: -6,
    scale: 0.98,
    transition: tFast,
  },
};

export const collapsible: Variants = {
  collapsed: { height: 0, opacity: 0 },
  expanded: { height: "auto", opacity: 1 },
};
