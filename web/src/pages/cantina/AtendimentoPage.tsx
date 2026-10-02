import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Search,
  ShoppingCart,
  User,
  UserSearch,
} from "lucide-react";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import {
  cantinaStudentsApi,
  cantinaConsumoApi,
  cantinaProductsApi,
  cantinaAutonomiaApi,
  type CantinaStudent,
  type Produto,
} from "../../api/endpoints";

function novaChaveIdempotencia(): string {
  return `consumo-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface CartItem {
  produto: Produto;
  quantidade: number;
}

function StudentCard({
  student,
  onSelect,
}: {
  student: CantinaStudent;
  onSelect: (s: CantinaStudent) => void;
}) {
  return (
    <button
      onClick={() => onSelect(student)}
      className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 transition-colors text-left"
    >
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
          <User className="h-5 w-5 text-primary-500" />
        </div>
        <div>
          <p className="font-medium text-gray-900 dark:text-gray-100">{student.nome}</p>
          <div className="flex items-center gap-2">
            {student.turma && (
              <p className="text-xs text-gray-500 dark:text-gray-400">Turma: {student.turma}</p>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                student.autonomia_cantina
                  ? "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400"
                  : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
              }`}
            >
              {student.autonomia_cantina ? "Autônomo" : "Sem autonomia"}
            </span>
          </div>
        </div>
      </div>
      <div className="text-right">
        <p className="text-xs text-gray-500 dark:text-gray-400">Saldo</p>
        <p className="font-semibold text-success-600 dark:text-success-400">
          {formatCurrency(student.saldo)}
        </p>
      </div>
    </button>
  );
}

function ConsumptionForm({
  student,
  onClose,
  onSuccess,
}: {
  student: CantinaStudent;
  onClose: () => void;
  onSuccess: (message: string) => void;
}) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const [cart, setCart] = useState<CartItem[]>([]);
  // Evita cobrança duplicada em retries/duplo clique no mesmo carrinho.
  const idempotencyKeyRef = useRef(novaChaveIdempotencia());

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ["cantina-products-active"],
    queryFn: () => cantinaProductsApi.list({ ativo: true, size: 100 }),
  });

  const availableProducts = (products?.items || []).filter(
    (p: Produto) => p.ativo && p.estoque_atual > 0,
  );

  const cartTotal = cart.reduce(
    (sum, item) => sum + item.produto.preco * item.quantidade,
    0,
  );

  const saldoRestante = student.saldo - cartTotal;

  const consumoMutation = useMutation({
    mutationFn: () =>
      cantinaConsumoApi.create({
        aluno_id: student.id,
        itens: cart.map((c) => ({
          produto_id: c.produto.id,
          quantidade: c.quantidade,
        })),
        idempotency_key: idempotencyKeyRef.current,
      }),
    onSuccess: () => {
      idempotencyKeyRef.current = novaChaveIdempotencia();
      queryClient.invalidateQueries({ queryKey: ["cantina-orders"] });
      queryClient.invalidateQueries({ queryKey: ["cantina-students"] });
      queryClient.invalidateQueries({ queryKey: ["cantina-dashboard"] });
      onSuccess(
        `Consumo de ${formatCurrency(cartTotal)} registrado para ${student.nome}.`,
      );
    },
  });

  const autonomiaMutation = useMutation({
    mutationFn: () => cantinaAutonomiaApi.set(student.id, true),
    onSuccess: () => {
      toast("success", "Autonomia habilitada para o aluno");
      queryClient.invalidateQueries({ queryKey: ["cantina-students"] });
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao habilitar autonomia");
    },
  });

  const updateQuantity = (produto: Produto, delta: number) => {
    setCart((prev) => {
      const existing = prev.find((c) => c.produto.id === produto.id);
      if (existing) {
        const newQty = existing.quantidade + delta;
        if (newQty <= 0) return prev.filter((c) => c.produto.id !== produto.id);
        return prev.map((c) =>
          c.produto.id === produto.id ? { ...c, quantidade: newQty } : c,
        );
      }
      if (delta > 0) return [...prev, { produto, quantidade: 1 }];
      return prev;
    });
  };

  if (!student.autonomia_cantina) {
    return (
      <Card>
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="h-5 w-5 text-warning-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {student.nome}
          </h3>
        </div>
        <div className="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-4">
          <p className="text-sm text-warning-700 dark:text-warning-300">
            Este aluno não possui autorização para escolher o próprio lanche.
          </p>
          <p className="text-xs text-warning-600 dark:text-warning-400 mt-1">
            O responsável deve habilitar a autonomia no aplicativo mobile.
          </p>
        </div>
        <div className="flex items-center gap-3 mt-4">
          <Button variant="ghost" onClick={onClose}>
            Fechar
          </Button>
          {user?.perfil === "admin" && (
            <Button
              onClick={() => autonomiaMutation.mutate()}
              loading={autonomiaMutation.isPending}
            >
              Habilitar autonomia
            </Button>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <ShoppingCart className="h-5 w-5 text-primary-500" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Consumo Direto
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {student.nome} — Saldo: {formatCurrency(student.saldo)}
            </p>
          </div>
        </div>
        <Button variant="ghost" onClick={onClose}>
          Fechar
        </Button>
      </div>

      {productsLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : (
        <>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {availableProducts.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">
                Nenhum produto disponível.
              </p>
            ) : (
              availableProducts.map((produto: Produto) => {
                const cartItem = cart.find((c) => c.produto.id === produto.id);
                const qty = cartItem?.quantidade || 0;

                return (
                  <div
                    key={produto.id}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                        {produto.nome}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Estoque: {produto.estoque_atual} — {formatCurrency(produto.preco)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQuantity(produto, -1)}
                        disabled={qty === 0}
                        className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center disabled:opacity-30"
                      >
                        −
                      </button>
                      <span className="w-6 text-center text-sm font-medium text-gray-900 dark:text-gray-100">
                        {qty}
                      </span>
                      <button
                        onClick={() => updateQuantity(produto, 1)}
                        disabled={qty >= produto.estoque_atual}
                        className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 flex items-center justify-center disabled:opacity-30"
                      >
                        +
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {cart.length > 0 && (
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <div className="space-y-1 mb-3">
                {cart.map((c) => (
                  <div key={c.produto.id} className="flex justify-between text-sm">
                    <span className="text-gray-700 dark:text-gray-300">
                      {c.produto.nome} × {c.quantidade}
                    </span>
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      {formatCurrency(c.produto.preco * c.quantidade)}
                    </span>
                  </div>
                ))}
              </div>
              <div className="border-t border-gray-200 dark:border-gray-700 pt-2">
                <div className="flex justify-between">
                  <span className="font-semibold text-gray-900 dark:text-gray-100">Total</span>
                  <span className="font-bold text-gray-900 dark:text-gray-100">
                    {formatCurrency(cartTotal)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Saldo após consumo
                  </span>
                  <span
                    className={`text-sm font-medium ${
                      saldoRestante < 0
                        ? "text-danger-600 dark:text-danger-400"
                        : "text-success-600 dark:text-success-400"
                    }`}
                  >
                    {formatCurrency(saldoRestante)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {consumoMutation.isError && (
            <div className="mt-3 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
              <p className="text-sm text-danger-600 dark:text-danger-400">
                {(consumoMutation.error as Error)?.message || "Erro ao registrar consumo"}
              </p>
            </div>
          )}

          <div className="mt-4 flex gap-2">
            <Button
              variant="primary"
              onClick={() => consumoMutation.mutate()}
              disabled={cart.length === 0 || saldoRestante < 0 || consumoMutation.isPending}
              loading={consumoMutation.isPending}
              className="flex-1"
            >
              {consumoMutation.isPending
                ? "Registrando..."
                : saldoRestante < 0
                  ? "Saldo insuficiente"
                  : "Confirmar consumo"}
            </Button>
          </div>
        </>
      )}
    </Card>
  );
}

export function AtendimentoPage() {
  const [query, setQuery] = useState("");
  const [selectedStudent, setSelectedStudent] = useState<CantinaStudent | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data: students, isLoading, isFetching } = useQuery({
    queryKey: ["cantina-students", query],
    queryFn: () => cantinaStudentsApi.search(query),
    enabled: query.length >= 2,
  });

  const results = students || [];

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: "Atendimento" }]} />

      <PageHeader
        title="Atendimento na Cantina"
        description="Consulte o aluno pelo nome, confira o saldo e registre o consumo direto"
      />

      {successMessage && (
        <div className="flex items-center gap-2 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
          <CheckCircle2 className="h-4 w-4 text-success-600 dark:text-success-400" />
          <p className="text-sm text-success-600 dark:text-success-400">{successMessage}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center gap-2 mb-4">
            <Search className="h-5 w-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Consultar Aluno
            </h2>
          </div>

          <Input
            label="Pesquisar aluno por nome..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          {query.length < 2 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <UserSearch className="h-10 w-10 text-gray-300 dark:text-gray-600 mb-2" />
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Digite pelo menos 2 caracteres para buscar.
              </p>
            </div>
          ) : isLoading || isFetching ? (
            <div className="flex justify-center py-6">
              <Spinner />
            </div>
          ) : results.length === 0 ? (
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-4 text-center">
              Nenhum aluno encontrado para "{query}".
            </p>
          ) : (
            <div className="space-y-2 mt-4">
              {results.map((student) => (
                <StudentCard
                  key={student.id}
                  student={student}
                  onSelect={(s) => {
                    setSuccessMessage(null);
                    setSelectedStudent(s);
                  }}
                />
              ))}
            </div>
          )}
        </Card>

        <div>
          {selectedStudent ? (
            <ConsumptionForm
              student={selectedStudent}
              onClose={() => setSelectedStudent(null)}
              onSuccess={(message) => {
                setSelectedStudent(null);
                setSuccessMessage(message);
              }}
            />
          ) : (
            <Card>
              <div className="flex flex-col items-center py-16 text-center">
                <ShoppingCart className="h-10 w-10 text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Selecione um aluno para registrar o consumo direto.
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  O aluno precisa possuir autonomia habilitada pelo responsável.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}