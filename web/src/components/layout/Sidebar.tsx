import { useEffect, useCallback } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  ChevronDown, ChevronRight, LogOut, Moon, Sun, X,
} from "lucide-react";
import { clsx } from "clsx";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { navMap, type NavItem } from "../../lib/navigation";
import { useState } from "react";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

function NavGroup({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const [open, setOpen] = useState(true);
  const location = useLocation();
  const isActive = item.children?.some((c) => location.pathname.startsWith(c.path || ""));

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={clsx(
          "flex items-center w-full px-3 py-2 text-sm rounded-lg transition-colors",
          isActive
            ? "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400"
            : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700/50",
        )}
      >
        <item.icon className="h-5 w-5 mr-3 flex-shrink-0" />
        <span className="flex-1 text-left">{item.label}</span>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open && item.children && (
        <div className="ml-4 mt-1 space-y-1">
          {item.children.map((child) => (
            <NavLink
              key={child.path}
              to={child.path || "#"}
              onClick={onNavigate}
              className={({ isActive }) =>
                clsx(
                  "flex items-center px-3 py-2 text-sm rounded-lg transition-colors",
                  isActive
                    ? "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400"
                    : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700/50",
                )
              }
            >
              <child.icon className="h-4 w-4 mr-3 flex-shrink-0" />
              {child.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

function NavLinkItem({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  if (item.children) {
    return <NavGroup item={item} onNavigate={onNavigate} />;
  }
  return (
    <NavLink
      to={item.path || "#"}
      onClick={onNavigate}
      className={({ isActive }) =>
        clsx(
          "flex items-center px-3 py-2 text-sm rounded-lg transition-colors",
          isActive
            ? "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400"
            : "text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700/50",
        )
      }
    >
      <item.icon className="h-5 w-5 mr-3 flex-shrink-0" />
      {item.label}
    </NavLink>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const perfil = user?.perfil || "admin";
  const navItems = navMap[perfil] || [];

  return (
    <>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <img src="/logo.png" alt="ePass" className="h-16 mx-auto object-contain" />
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {navItems.map((item) => (
          <NavLinkItem key={item.label} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="p-3 border-t border-gray-200 dark:border-gray-700 space-y-1">
        <button
          onClick={toggleTheme}
          className="flex items-center w-full px-3 py-2 text-sm rounded-lg text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700/50 transition-colors"
        >
          {theme === "dark" ? <Sun className="h-5 w-5 mr-3" /> : <Moon className="h-5 w-5 mr-3" />}
          {theme === "dark" ? "Tema Claro" : "Tema Escuro"}
        </button>
        <button
          onClick={logout}
          className="flex items-center w-full px-3 py-2 text-sm rounded-lg text-danger-500 hover:bg-danger-50 dark:hover:bg-danger-900/20 transition-colors"
        >
          <LogOut className="h-5 w-5 mr-3" />
          Sair
        </button>
      </div>
    </>
  );
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
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
        <SidebarContent />
      </aside>

      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          "fixed top-0 left-0 z-50 h-screen w-64 bg-card dark:bg-card-dark border-r border-gray-200 dark:border-gray-700 flex flex-col transition-transform duration-300 ease-in-out md:hidden",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-end p-4 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <SidebarContent onNavigate={onClose} />
      </aside>
    </>
  );
}
