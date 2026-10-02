import type { ReactNode } from "react";
import { useEffect } from "react";
import {
  animate,
  motion,
  useMotionValue,
  useReducedMotion,
  useTransform,
} from "framer-motion";
import { EASE_EPASS, springSoft, tBase, tFast } from "./transitions";

type Direction = "up" | "down" | "left" | "right" | "none";

interface RevealProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  direction?: Direction;
  distance?: number;
  duration?: number;
  once?: boolean;
  amount?: number;
}

function offsetFor(direction: Direction, distance: number) {
  switch (direction) {
    case "up":
      return { y: distance };
    case "down":
      return { y: -distance };
    case "left":
      return { x: distance };
    case "right":
      return { x: -distance };
    default:
      return {};
  }
}

export function Reveal({
  children,
  className,
  delay = 0,
  direction = "up",
  distance = 16,
  duration,
  once = true,
  amount = 0.2,
}: RevealProps) {
  const reduceMotion = useReducedMotion();
  const offset = offsetFor(direction, distance);
  const transition = reduceMotion
    ? { duration: 0.01 }
    : { duration: duration ?? tBase.duration, ease: EASE_EPASS, delay };

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, ...(reduceMotion ? {} : offset) }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once, amount }}
      transition={transition}
    >
      {children}
    </motion.div>
  );
}

interface StaggerProps {
  children: ReactNode;
  className?: string;
  interval?: number;
  delay?: number;
  amount?: number;
  once?: boolean;
}

export function Stagger({
  children,
  className,
  interval = 0.05,
  delay = 0.03,
  amount = 0.15,
  once = true,
}: StaggerProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, amount }}
      variants={{
        hidden: {},
        visible: reduceMotion
          ? {}
          : { transition: { staggerChildren: interval, delayChildren: delay } },
      }}
    >
      {children}
    </motion.div>
  );
}

interface StaggerItemProps {
  children: ReactNode;
  className?: string;
  distance?: number;
  duration?: number;
  layout?: boolean;
}

export function StaggerItem({
  children,
  className,
  distance = 14,
  duration,
  layout,
}: StaggerItemProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      layout={layout}
      variants={{
        hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, y: distance },
        visible: {
          opacity: 1,
          y: 0,
          transition: reduceMotion
            ? { duration: 0.01 }
            : { duration: duration ?? tBase.duration, ease: EASE_EPASS },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

interface ScalePopProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  once?: boolean;
  amount?: number;
}

export function ScalePop({
  children,
  className,
  delay = 0,
  once = true,
  amount = 0.3,
}: ScalePopProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, scale: reduceMotion ? 1 : 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once, amount }}
      transition={reduceMotion ? { duration: 0.01 } : { ...springSoft, delay }}
    >
      {children}
    </motion.div>
  );
}

interface CountUpProps {
  value: number;
  duration?: number;
  className?: string;
  decimals?: number;
  prefix?: string;
  suffix?: string;
}

export function CountUp({
  value,
  duration = 0.9,
  className,
  decimals = 0,
  prefix = "",
  suffix = "",
}: CountUpProps) {
  const reduceMotion = useReducedMotion();
  const count = useMotionValue(0);
  const display = useTransform(count, (v) =>
    v.toLocaleString("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }),
  );

  useEffect(() => {
    if (reduceMotion || !Number.isFinite(value)) {
      count.set(Number.isFinite(value) ? value : 0);
      return;
    }
    const controls = animate(count, value, { duration, ease: "easeOut" });
    return () => controls.stop();
  }, [count, value, duration, reduceMotion]);

  return (
    <motion.span className={className} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={tFast}>
      {prefix}
      <motion.span>{display}</motion.span>
      {suffix}
    </motion.span>
  );
}
