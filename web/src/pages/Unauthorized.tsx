import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

export function Unauthorized() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface dark:bg-surface-dark p-4">
      <Card className="max-w-md text-center">
        <h1 className="text-6xl font-bold text-danger-500">403</h1>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-4">Acesso Negado</h2>
        <p className="text-gray-500 dark:text-gray-400 mt-2">
          Você não tem permissão para acessar esta página.
        </p>
        <div className="mt-6 flex gap-3 justify-center">
          <Button variant="outline" onClick={() => navigate(-1)}>
            Voltar
          </Button>
          <Button onClick={() => navigate("/")}>Ir para o Dashboard</Button>
        </div>
      </Card>
    </div>
  );
}
