import { useAuth } from "../contexts/AuthContext";
import { Card } from "../components/ui/Card";

export function Dashboard() {
  const { user } = useAuth();

  const perfilLabel: Record<string, string> = {
    admin: "Administrativo",
    secretaria: "Secretaria",
    coordenador: "Coordenação",
    professor: "Docente",
    responsavel: "Responsável",
    cantineiro: "Cantina",
  };
  const label = perfilLabel[user?.perfil || "admin"];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Bem-vindo, {user?.nome} — Painel {label}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">—</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Em breve</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">—</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Em breve</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">—</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Em breve</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">—</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Em breve</p>
        </Card>
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Módulos disponíveis
        </h2>
        <p className="text-gray-500 dark:text-gray-400">
          Use a barra lateral para navegar entre os módulos do sistema. Os CRUDs serão implementados nas próximas fases.
        </p>
      </Card>
    </div>
  );
}
