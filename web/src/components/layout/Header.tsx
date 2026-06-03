import { Menu } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user } = useAuth();

  return (
    <header className="h-16 bg-card dark:bg-card-dark border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4 md:px-6 gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 md:hidden flex-shrink-0"
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="text-right">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate max-w-[120px] md:max-w-none">
            {user?.nome}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{user?.perfil}</p>
        </div>
        <div className="h-9 w-9 rounded-full bg-primary-500 flex items-center justify-center text-white font-medium text-sm flex-shrink-0">
          {user?.nome?.charAt(0)?.toUpperCase() || "U"}
        </div>
      </div>
    </header>
  );
}
