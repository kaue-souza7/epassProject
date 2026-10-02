import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Package,
  Plus,
  Pencil,
  ToggleLeft,
  ToggleRight,
  Boxes,
  Image as ImageIcon,
  Upload,
  X,
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Badge } from "../../components/ui/Badge";
import { Spinner } from "../../components/ui/Spinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton } from "../../components/ui/Skeleton";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Modal } from "../../components/ui/Modal";
import {
  cantinaProductsApi,
  cantinaStockHistoryApi,
  cantinaUploadApi,
  type Produto,
  type ProdutoCreateRequest,
  type CategoriaProduto,
  CATEGORIA_PRODUTO_LABELS,
} from "../../api/endpoints";

type StatusFilter = "ativos" | "inativos" | "todos";

const WRITE_ROLES = ["admin", "cantineiro"];
const STOCK_ROLES = ["admin", "cantineiro"];

const UNIDADE_OPTIONS = [
  { value: "un", label: "Unidade" },
  { value: "kg", label: "Quilograma" },
  { value: "g", label: "Grama" },
  { value: "l", label: "Litro" },
  { value: "ml", label: "Mililitro" },
];

const CATEGORIA_OPTIONS = [
  { value: "", label: "Todas" },
  ...Object.entries(CATEGORIA_PRODUTO_LABELS).map(([value, label]) => ({ value, label })),
];

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function getStockBadge(produto: Produto) {
  if (!produto.ativo) return <Badge variant="default">Inativo</Badge>;
  if (produto.estoque_atual === 0) return <Badge variant="danger">Sem Estoque</Badge>;
  if (produto.estoque_minimo > 0 && produto.estoque_atual <= produto.estoque_minimo)
    return <Badge variant="warning">Estoque Baixo</Badge>;
  return <Badge variant="success">Disponível</Badge>;
}

function ProductCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <Skeleton className="h-40 w-full rounded-none" />
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-24" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-8 w-16" />
        </div>
      </div>
    </div>
  );
}

export function CadastroPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const canAdjustStock = user?.perfil && STOCK_ROLES.includes(user.perfil);

  const [search, setSearch] = useState("");
  const [categoriaFilter, setCategoriaFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ativos");
  const [showForm, setShowForm] = useState(false);
  const [editingProduto, setEditingProduto] = useState<Produto | null>(null);
  const [estoqueProduto, setEstoqueProduto] = useState<Produto | null>(null);
  const [toggleConfirm, setToggleConfirm] = useState<Produto | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["cantina-products"],
    queryFn: () => cantinaProductsApi.list({ size: 100 }),
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => cantinaProductsApi.toggle(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cantina-products"] });
      setToggleConfirm(null);
      toast("success", "Produto atualizado com sucesso");
    },
    onError: () => {
      toast("error", "Erro ao atualizar produto");
    },
  });

  const produtos = data?.items || [];

  const filtered = produtos.filter((p) => {
    const matchesSearch = !search || p.nome.toLowerCase().includes(search.toLowerCase());
    const matchesCategoria = !categoriaFilter || p.categoria === categoriaFilter;
    const matchesStatus =
      statusFilter === "todos" ||
      (statusFilter === "ativos" && p.ativo) ||
      (statusFilter === "inativos" && !p.ativo);
    return matchesSearch && matchesCategoria && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: "Cantina" }, { label: "Cadastro" }]} />

      <PageHeader
        title="Cadastro de Produtos"
        description={`${produtos.length} produto(s) cadastrado(s)`}
      >
        {canWrite && (
          <Button
            variant="primary"
            onClick={() => {
              setEditingProduto(null);
              setShowForm(true);
            }}
          >
            <Plus className="h-4 w-4 mr-1" /> Novo Produto
          </Button>
        )}
      </PageHeader>

      <div className="flex flex-col sm:flex-row gap-3">
        <Input
          label="Buscar produto"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="sm:w-64"
          placeholder="Nome do produto..."
        />
        <div className="flex-1">
          <Select
            label="Categoria"
            value={categoriaFilter}
            onChange={(e) => setCategoriaFilter(e.target.value)}
            options={CATEGORIA_OPTIONS}
          />
        </div>
        <div className="flex-1">
          <Select
            label="Status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            options={[
              { value: "ativos", label: "Ativos" },
              { value: "inativos", label: "Inativos" },
              { value: "todos", label: "Todos" },
            ]}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <ProductCardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Package}
          title="Nenhum produto encontrado"
          description={
            canWrite
              ? "Clique em 'Novo Produto' para cadastrar."
              : "Nenhum produto disponível."
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((produto) => (
            <div
              key={produto.id}
              className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col ${
                !produto.ativo ? "opacity-60" : ""
              }`}
            >
              <div className="h-40 bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                {produto.imagem_url ? (
                  <img
                    src={produto.imagem_url}
                    alt={produto.nome}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <ImageIcon className="h-10 w-10 text-gray-300 dark:text-gray-600" />
                )}
              </div>

              <div className="p-4 flex flex-col flex-1">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm leading-tight">
                    {produto.nome}
                  </h3>
                  <Badge variant={produto.ativo ? "success" : "danger"}>
                    {produto.ativo ? "Ativo" : "Inativo"}
                  </Badge>
                </div>

                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 self-start mb-2">
                  {CATEGORIA_PRODUTO_LABELS[produto.categoria]}
                </span>

                <p className="text-lg font-bold text-primary-500 mb-1">
                  {formatCurrency(produto.preco)}
                </p>

                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Estoque: {produto.estoque_atual}
                    {produto.estoque_minimo > 0 && ` (mín: ${produto.estoque_minimo})`}
                  </span>
                  {getStockBadge(produto)}
                </div>

                <div className="flex gap-1 flex-wrap mt-auto">
                  {canAdjustStock && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setEstoqueProduto(produto)}
                    >
                      <Boxes className="h-3.5 w-3.5 mr-1" /> Estoque
                    </Button>
                  )}
                  {canWrite && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditingProduto(produto);
                          setShowForm(true);
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5 mr-1" /> Editar
                      </Button>
                      <Button
                        size="sm"
                        variant={produto.ativo ? "danger" : "primary"}
                        onClick={() => setToggleConfirm(produto)}
                      >
                        {produto.ativo ? (
                          <>
                            <ToggleLeft className="h-3.5 w-3.5 mr-1" /> Desativar
                          </>
                        ) : (
                          <>
                            <ToggleRight className="h-3.5 w-3.5 mr-1" /> Ativar
                          </>
                        )}
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ProdutoFormModal
        open={showForm}
        produto={editingProduto}
        onClose={() => {
          setShowForm(false);
          setEditingProduto(null);
        }}
      />

      <EstoqueModal
        open={!!estoqueProduto}
        produto={estoqueProduto}
        onClose={() => setEstoqueProduto(null)}
      />

      <ConfirmDialog
        open={!!toggleConfirm}
        title={toggleConfirm?.ativo ? "Desativar Produto" : "Ativar Produto"}
        message={`Tem certeza que deseja ${toggleConfirm?.ativo ? "desativar" : "ativar"} o produto "${toggleConfirm?.nome}"?`}
        confirmLabel={toggleConfirm?.ativo ? "Desativar" : "Ativar"}
        variant={toggleConfirm?.ativo ? "danger" : "primary"}
        loading={toggleMutation.isPending}
        onConfirm={() => toggleConfirm && toggleMutation.mutate(toggleConfirm.id)}
        onCancel={() => setToggleConfirm(null)}
      />
    </div>
  );
}

function ProdutoFormModal({
  open,
  produto,
  onClose,
}: {
  open: boolean;
  produto: Produto | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const isEditing = !!produto;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [nome, setNome] = useState("");
  const [codigo, setCodigo] = useState("");
  const [categoria, setCategoria] = useState<CategoriaProduto>("SALGADO");
  const [descricao, setDescricao] = useState("");
  const [preco, setPreco] = useState("");
  const [custo, setCusto] = useState("");
  const [estoqueAtual, setEstoqueAtual] = useState("");
  const [estoqueMinimo, setEstoqueMinimo] = useState("");
  const [unidadeMedida, setUnidadeMedida] = useState("un");
  const [perecivel, setPerecivel] = useState(false);
  const [dataValidade, setDataValidade] = useState("");
  const [imagemUrl, setImagemUrl] = useState<string | null>(null);
  const [imagemPreview, setImagemPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) return;
    if (produto) {
      setNome(produto.nome);
      setCodigo(produto.codigo || "");
      setCategoria(produto.categoria);
      setDescricao(produto.descricao || "");
      setPreco(String(produto.preco));
      setCusto(produto.custo != null ? String(produto.custo) : "");
      setEstoqueAtual(String(produto.estoque_atual));
      setEstoqueMinimo(String(produto.estoque_minimo));
      setUnidadeMedida(produto.unidade_medida || "un");
      setPerecivel(produto.perecivel);
      setDataValidade(produto.data_validade || "");
      setImagemUrl(produto.imagem_url);
      setImagemPreview(produto.imagem_url);
    } else {
      setNome("");
      setCodigo("");
      setCategoria("SALGADO");
      setDescricao("");
      setPreco("");
      setCusto("");
      setEstoqueAtual("0");
      setEstoqueMinimo("0");
      setUnidadeMedida("un");
      setPerecivel(false);
      setDataValidade("");
      setImagemUrl(null);
      setImagemPreview(null);
    }
    setErrors({});
  }, [open, produto]);

  const createMutation = useMutation({
    mutationFn: (data: ProdutoCreateRequest) => cantinaProductsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cantina-products"] });
      toast("success", "Produto criado com sucesso");
      onClose();
    },
    onError: () => {
      toast("error", "Erro ao criar produto");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: ProdutoCreateRequest) =>
      cantinaProductsApi.update(produto!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cantina-products"] });
      toast("success", "Produto atualizado com sucesso");
      onClose();
    },
    onError: () => {
      toast("error", "Erro ao atualizar produto");
    },
  });

  function validate(): boolean {
    const newErrors: Record<string, string> = {};
    if (!nome.trim()) newErrors.nome = "Nome é obrigatório";
    if (!preco || parseFloat(preco) <= 0) newErrors.preco = "Preço deve ser maior que 0";
    if (!categoria) newErrors.categoria = "Categoria é obrigatória";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;

    const payload: ProdutoCreateRequest = {
      nome: nome.trim(),
      descricao: descricao.trim() || undefined,
      preco: parseFloat(preco),
      custo: custo ? parseFloat(custo) : undefined,
      imagem_url: imagemUrl || undefined,
      categoria,
      estoque_atual: isEditing ? undefined : parseInt(estoqueAtual) || 0,
      estoque_minimo: parseInt(estoqueMinimo) || 0,
      codigo: codigo.trim() || undefined,
      unidade_medida: unidadeMedida || undefined,
      perecivel,
      data_validade: perecivel && dataValidade ? dataValidade : undefined,
    };

    if (isEditing) {
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate(payload);
    }
  }

  async function handleImageUpload(file: File) {
    if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
      toast("error", "Formato inválido. Use JPG, PNG ou WebP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast("error", "Imagem deve ter no máximo 5MB.");
      return;
    }

    setUploading(true);
    try {
      const preview = URL.createObjectURL(file);
      setImagemPreview(preview);
      const result = await cantinaUploadApi.upload(file);
      setImagemUrl(result.url);
      toast("success", "Imagem enviada com sucesso");
    } catch {
      toast("error", "Erro ao enviar imagem");
      setImagemPreview(null);
    } finally {
      setUploading(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleImageUpload(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleImageUpload(file);
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  if (!open) return null;

  return (
    <Modal
      open={open}
      title={isEditing ? "Editar Produto" : "Novo Produto"}
      onClose={onClose}
      size="lg"
    >
      <div className="space-y-4">
        <div
          className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-4 text-center hover:border-primary-400 transition-colors cursor-pointer"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp"
            className="hidden"
            onChange={handleFileChange}
          />
          {uploading ? (
            <div className="py-6">
              <Spinner />
              <p className="text-sm text-gray-500 mt-2">Enviando imagem...</p>
            </div>
          ) : imagemPreview ? (
            <div className="relative inline-block">
              <img
                src={imagemPreview}
                alt="Preview"
                className="h-32 rounded-lg object-cover"
              />
              <button
                type="button"
                className="absolute -top-2 -right-2 bg-danger-500 text-white rounded-full p-1 hover:bg-danger-600"
                onClick={(e) => {
                  e.stopPropagation();
                  setImagemPreview(null);
                  setImagemUrl(null);
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ) : (
            <div className="py-6">
              <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                Arraste uma imagem ou clique para selecionar
              </p>
              <p className="text-xs text-gray-400 mt-1">JPG, PNG ou WebP, máx. 5MB</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <Input
              label="Nome"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              error={errors.nome}
            />
          </div>
          <Input
            label="Código"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />
          <div>
            <Select
              label="Categoria"
              value={categoria}
              onChange={(e) => setCategoria(e.target.value as CategoriaProduto)}
              options={Object.entries(CATEGORIA_PRODUTO_LABELS).map(([value, label]) => ({
                value,
                label,
              }))}
              error={errors.categoria}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Descrição
          </label>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 text-gray-900 dark:text-gray-100 resize-none"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Preço de Venda (R$)"
            type="number"
            step="0.01"
            min="0"
            value={preco}
            onChange={(e) => setPreco(e.target.value)}
            error={errors.preco}
          />
          <Input
            label="Custo (R$)"
            type="number"
            step="0.01"
            min="0"
            value={custo}
            onChange={(e) => setCusto(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {!isEditing && (
            <Input
              label="Estoque Atual"
              type="number"
              min="0"
              value={estoqueAtual}
              onChange={(e) => setEstoqueAtual(e.target.value)}
            />
          )}
          <Input
            label="Estoque Mínimo"
            type="number"
            min="0"
            value={estoqueMinimo}
            onChange={(e) => setEstoqueMinimo(e.target.value)}
          />
          <div>
            <Select
              label="Unidade de Medida"
              value={unidadeMedida}
              onChange={(e) => setUnidadeMedida(e.target.value)}
              options={UNIDADE_OPTIONS}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={perecivel}
              onChange={(e) => {
                setPerecivel(e.target.checked);
                if (!e.target.checked) setDataValidade("");
              }}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-gray-200 peer-focus:ring-2 peer-focus:ring-primary-500 rounded-full peer dark:bg-gray-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-500" />
          </label>
          <span className="text-sm text-gray-700 dark:text-gray-300">Produto Perecível</span>
        </div>

        {perecivel && (
          <Input
            label="Data de Validade"
            type="date"
            value={dataValidade}
            onChange={(e) => setDataValidade(e.target.value)}
          />
        )}

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <Button variant="ghost" onClick={onClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={isPending}>
            {isEditing ? "Salvar" : "Criar"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function EstoqueModal({
  open,
  produto,
  onClose,
}: {
  open: boolean;
  produto: Produto | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [operacao, setOperacao] = useState<"entrada" | "saida">("entrada");
  const [quantidade, setQuantidade] = useState("");
  const [motivo, setMotivo] = useState("");

  const estoqueAtual = produto?.estoque_atual ?? 0;
  const qtd = parseInt(quantidade) || 0;
  const novoEstoque = operacao === "entrada" ? estoqueAtual + qtd : estoqueAtual - qtd;
  const isInvalid = operacao === "saida" && qtd > estoqueAtual;

  const { data: historico, isLoading: historicoLoading } = useQuery({
    queryKey: ["cantina-stock-history", produto?.id],
    queryFn: () => cantinaStockHistoryApi.list(produto!.id, { size: 10 }),
    enabled: open && !!produto,
  });

  const mutation = useMutation({
    mutationFn: () =>
      cantinaProductsApi.adjustStock(produto!.id, {
        quantidade: operacao === "entrada" ? qtd : -qtd,
        motivo: motivo || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cantina-products"] });
      queryClient.invalidateQueries({ queryKey: ["cantina-stock-history"] });
      setQuantidade("");
      setMotivo("");
      setOperacao("entrada");
      toast("success", "Estoque ajustado com sucesso");
      onClose();
    },
    onError: () => {
      toast("error", "Erro ao ajustar estoque");
    },
  });

  if (!open || !produto) return null;

  return (
    <Modal open={open} title="Ajustar Estoque" onClose={onClose}>
      <div className="space-y-4">
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <p className="text-sm text-gray-500 dark:text-gray-400">Produto</p>
          <p className="font-medium text-gray-900 dark:text-gray-100">
            {produto.nome}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
            Estoque atual:{" "}
            <span className="font-semibold">{estoqueAtual}</span>
          </p>
        </div>

        <div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Últimas movimentações
          </p>
          {historicoLoading ? (
            <Spinner size="sm" />
          ) : !historico?.items?.length ? (
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Nenhuma movimentação registrada.
            </p>
          ) : (
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {historico.items.map((m) => (
                <div
                  key={m.id}
                  className="flex items-center justify-between text-xs bg-gray-50 dark:bg-gray-800 rounded px-2 py-1.5"
                >
                  <div>
                    <span
                      className={
                        m.tipo === "entrada"
                          ? "text-success-600 dark:text-success-400 font-medium"
                          : "text-danger-600 dark:text-danger-400 font-medium"
                      }
                    >
                      {m.tipo === "entrada" ? "+" : "-"}
                      {m.quantidade}
                    </span>
                    <span className="text-gray-500 dark:text-gray-400 ml-2">
                      {m.motivo || "Ajuste manual"}
                    </span>
                  </div>
                  <span className="text-gray-400 dark:text-gray-500">
                    {new Date(m.created_at).toLocaleDateString("pt-BR")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Operação
          </p>
          <div className="flex gap-2">
            <Button
              variant={operacao === "entrada" ? "primary" : "outline"}
              onClick={() => setOperacao("entrada")}
            >
              Entrada
            </Button>
            <Button
              variant={operacao === "saida" ? "danger" : "outline"}
              onClick={() => setOperacao("saida")}
            >
              Saída
            </Button>
          </div>
        </div>

        <Input
          label="Quantidade"
          type="number"
          min="1"
          value={quantidade}
          onChange={(e) => setQuantidade(e.target.value)}
          error={isInvalid ? "Quantidade não pode exceder o estoque" : undefined}
        />

        <Input
          label="Motivo (opcional)"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />

        {qtd > 0 && (
          <div
            className={`rounded-lg p-3 ${
              isInvalid
                ? "bg-red-50 dark:bg-red-900/20"
                : "bg-green-50 dark:bg-green-900/20"
            }`}
          >
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Novo estoque:
            </p>
            <p
              className={`text-lg font-bold ${
                isInvalid
                  ? "text-red-600 dark:text-red-400"
                  : "text-green-600 dark:text-green-400"
              }`}
            >
              {isInvalid ? `${novoEstoque} (inválido)` : novoEstoque}
            </p>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            loading={mutation.isPending}
            disabled={qtd <= 0 || isInvalid}
            onClick={() => mutation.mutate()}
          >
            Confirmar
          </Button>
        </div>
      </div>
    </Modal>
  );
}
