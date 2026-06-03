import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { studentsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Spinner } from "../../components/ui/Spinner";
import { Users, UserCheck, UserX } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";

export function MyChildren() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;

  const { data: children, isLoading, isError } = useQuery({
    queryKey: ["my-children"],
    queryFn: studentsApi.myChildren,
  });

  if (isLoading) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Meus Filhos" }]} />
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      </div>
    );
  }

  const queryClient = useQueryClient();

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Meus Filhos" }]} />
        <Card>
          <ErrorState
            title="Erro ao carregar dados"
            message="Não foi possível carregar a lista de filhos."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["my-children"] })}
          />
        </Card>
      </div>
    );
  }

  if (!children || children.length === 0) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Meus Filhos" }]} />
        <Card>
          <div className="text-center py-12">
            <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">
              Nenhum filho vinculado ao seu cadastro.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Meus Filhos" }]} />
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Meus Filhos</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Selecione um filho para visualizar detalhes acadêmicos
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {children.map((child) => (
          <Card
            key={child.id}
            className="cursor-pointer hover:shadow-md transition-shadow"
          >
            <div
              role="button"
              tabIndex={0}
              className="flex items-center gap-3"
              onClick={() => navigate(`${prefix}/meus-filhos/${child.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  navigate(`${prefix}/meus-filhos/${child.id}`);
                }
              }}
            >
              {child.ativo ? (
                <UserCheck className="h-10 w-10 text-primary-500 flex-shrink-0" />
              ) : (
                <UserX className="h-10 w-10 text-gray-400 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-base font-medium text-gray-900 dark:text-gray-100 truncate">
                  {child.nome}
                </p>
                <div className="mt-1">
                  <Badge variant={child.ativo ? "success" : "danger"}>
                    {child.ativo ? "Ativo" : "Inativo"}
                  </Badge>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
