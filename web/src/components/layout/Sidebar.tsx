import { useEffect, useCallback, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { LogOut, Moon, Sun, X, type LucideIcon } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { navMap, type NavItem } from "../../lib/navigation";
import { BranchedMenu, type BranchedMenuItem } from "../ui/BranchedMenu";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

/** Prefixo das seções, para não colidir com valores que são rotas. */
const SECTION_PREFIX = "@";

function toBranchedItems(items: NavItem[]): BranchedMenuItem[] {
  return items.map((item) => ({
    value: item.path ?? `${SECTION_PREFIX}${item.label}`,
    label: item.label,
    icon: item.icon as LucideIcon,
    href: item.path,
    children: item.children
      ? item.children.map((child) => ({
          value: child.path ?? `${SECTION_PREFIX}${child.label}`,
          label: child.label,
          icon: child.icon as LucideIcon,
          href: child.path,
        }))
      : undefined,
  }));
}

/**
 * Descobre qual entrada do menu corresponde à rota atual. O prefixo mais
 * longo vence, então `/admin/alunos/123` cai em "Alunos" e não no item de raiz
 * mais genérico.
 */
function resolveActive(items: BranchedMenuItem[], pathname: string): string | undefined {
  let best: string | undefined;
  let bestLength = -1;
  for (const item of items) {
    if (item.href && item.href !== pathname && !pathname.startsWith(`${item.href}/`)) continue;
    if (item.href && item.href.length > bestLength) {
      best = item.value;
      bestLength = item.href.length;
    }
    for (const child of item.children ?? []) {
      if (!child.href) continue;
      if (child.href !== pathname && !pathname.startsWith(`${child.href}/`)) continue;
      if (child.href.length > bestLength) {
        best = child.value;
        bestLength = child.href.length;
      }
    }
  }
  return best;
}

function SidebarContent({ onNavigate, idPrefix }: { onNavigate?: () => void; idPrefix: string }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const reduceMotion = useReducedMotion();

  const perfil = user?.perfil || "admin";
  const items = useMemo(() => toBranchedItems(navMap[perfil] || []), [perfil]);
  const activeValue = useMemo(
    () => resolveActive(items, location.pathname),
    [items, location.pathname],
  );

  // Hoje todos os grupos começam abertos; mantém o mesmo alcance de navegação.
  const allSectionsOpen = useMemo(
    () => items.map((item, index) => (item.children ? index : -1)).filter((i) => i >= 0),
    [items],
  );

  const footerItems = useMemo<BranchedMenuItem[]>(
    () => [
      {
        value: `${idPrefix}:tema`,
        label: theme === "dark" ? "Tema Claro" : "Tema Escuro",
        icon: theme === "dark" ? Sun : Moon,
        trailing: (
          <span
            className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
            aria-hidden="true"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </span>
        ),
      },
      {
        value: `${idPrefix}:sair`,
        label: "Sair",
        icon: LogOut,
        tone: "danger",
      },
    ],
    [theme, idPrefix],
  );

  const handleSelect = useCallback(
    (value: string) => {
      if (value === `${idPrefix}:tema`) {
        toggleTheme();
      } else if (value === `${idPrefix}:sair`) {
        logout();
      } else {
        navigate(value);
      }
      onNavigate?.();
    },
    [idPrefix, navigate, onNavigate, logout, toggleTheme],
  );

  return (
    <>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <motion.img
          src="/logo.png"
          alt="ePass"
          className="h-16 mx-auto object-contain"
          whileHover={reduceMotion ? undefined : { scale: 1.06, rotate: -2 }}
          whileTap={reduceMotion ? undefined : { scale: 0.96 }}
        />
      </div>

      <div className="flex-1 overflow-y-auto py-3 pr-1 pl-3 epass-scrollbar">
        <BranchedMenu
          items={items}
          label={`Menu de ${perfil}`}
          activeValue={activeValue}
          defaultOpen={allSectionsOpen}
          onSelect={handleSelect}
          width={224}
          fontSize={14}
          rowHeight={38}
          indent={34}
        />
      </div>

      <div className="p-3 border-t border-gray-200 dark:border-gray-700">
        <BranchedMenu
          items={footerItems}
          label="Ações da conta"
          onSelect={handleSelect}
          width={224}
          fontSize={14}
          rowHeight={38}
          branchLeaves
        />
      </div>
    </>
  );
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const reduceMotion = useReducedMotion();

  const closeOnEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, closeOnEscape]);

  return (
    <>
      <aside className="hidden md:flex md:flex-col w-64 bg-card dark:bg-card-dark border-r border-gray-200 dark:border-gray-700 h-screen flex-shrink-0">
        <SidebarContent idPrefix="desktop" />
      </aside>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="backdrop"
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px] md:hidden"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
        )}
      </AnimatePresence>

      <motion.aside
        className="fixed top-0 left-0 z-50 h-screen w-64 max-w-[85vw] bg-card dark:bg-card-dark border-r border-gray-200 dark:border-gray-700 flex flex-col md:hidden"
        initial={false}
        animate={{ x: isOpen ? 0 : -300 }}
        transition={reduceMotion ? { duration: 0.01 } : { type: "spring", stiffness: 320, damping: 34 }}
      >
        <div className="flex items-center justify-end p-3 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            aria-label="Fechar menu"
            className="p-2 -mr-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <SidebarContent onNavigate={onClose} idPrefix="mobile" />
      </motion.aside>
    </>
  );
}
