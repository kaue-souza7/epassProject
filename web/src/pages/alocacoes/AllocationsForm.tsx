import { useState, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { allocationsApi, teachersApi, classesApi, subjectsApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { StepIndicator } from "../../components/ui/StepIndicator";
import { Search, UserCheck, School, BookOpen, Calendar, AlertCircle } from "lucide-react";

const allocationSchema = z.object({
  professor_id: z.string().min(1, "Selecione um professor"),
  turma_id: z.string().min(1, "Selecione uma turma"),
  disciplina_id: z.string().min(1, "Selecione uma disciplina"),
  data_inicio: z.string().min(1, "Data de início é obrigatória"),
});

type AllocationFormData = z.infer<typeof allocationSchema>;

const steps = ["Professor", "Turma", "Disciplina", "Confirmar"];

export function AllocationsForm() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const prefix = `/${user?.perfil}`;

  const {
    watch,
    setValue,
    trigger,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AllocationFormData>({
    resolver: zodResolver(allocationSchema),
    defaultValues: {
      professor_id: "",
      turma_id: "",
      disciplina_id: "",
      data_inicio: new Date().toISOString().split("T")[0],
    },
  });

  const professorId = watch("professor_id");
  const turmaId = watch("turma_id");
  const disciplinaId = watch("disciplina_id");
  const dataInicio = watch("data_inicio");

  const [step, setStep] = useState(0);
  const [search, setSearch] = useState("");

  const formTopRef = useRef<HTMLDivElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    formTopRef.current?.focus();
  }, [step]);

  const { data: teachersData, isLoading: loadingTeachers } = useQuery({
    queryKey: ["teachers", "all"],
    queryFn: () => teachersApi.list({ size: 100, only_active: true }),
  });

  const { data: classes } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list(),
    enabled: step >= 1,
  });

  const { data: subjects } = useQuery({
    queryKey: ["subjects"],
    queryFn: () => subjectsApi.list(),
    enabled: step >= 2,
  });

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
  });

  const serieMap = useMemo(() => new Map(series?.map((s) => [s.id, s]) ?? []), [series]);
  const anoMap = useMemo(() => new Map(anosLetivos?.map((a) => [a.id, a]) ?? []), [anosLetivos]);

  const professores = teachersData?.items ?? [];
  const filteredProfessores = search
    ? professores.filter((p) => {
        const nome = ((p as any).nome || "").toLowerCase();
        return nome.includes(search.toLowerCase());
      })
    : professores;

  const turmaOptions = (classes?.items ?? [])
    .filter((t) => t.ativo)
    .map((t) => {
      const serie = serieMap.get(t.serie_id);
      return {
        id: t.id,
        label: `${t.codigo} — ${serie?.nome ?? "?"} (${anoMap.get(t.ano_letivo_id)?.ano ?? "?"})`,
        vagas: t.vagas_total,
      };
    });

  const disciplinaOptions = (subjects ?? [])
    .filter((d) => d.ativo)
    .map((d) => ({
      id: d.id,
      label: `${d.codigo} — ${d.nome}`,
    }));

  const createMutation = useMutation({
    mutationFn: (data: AllocationFormData) =>
      allocationsApi.create({
        professor_id: data.professor_id,
        turma_id: data.turma_id,
        disciplina_id: data.disciplina_id,
        data_inicio: data.data_inicio,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["allocations"] });
      toast("success", "Alocação criada com sucesso");
      navigate(`${prefix}/alocacoes`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao criar alocação");
    },
  });

  useEffect(() => {
    if (errors.professor_id || errors.turma_id || errors.disciplina_id || errors.data_inicio) {
      errorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [errors]);

  const selectedProfessor = professorId
    ? { id: professorId, nome: (professores.find((p) => p.usuario_id === professorId) as any)?.nome ?? "" }
    : null;

  const selectedTurma = turmaId
    ? { id: turmaId, label: turmaOptions.find((t) => t.id === turmaId)?.label ?? "" }
    : null;

  const selectedDisciplina = disciplinaId
    ? { id: disciplinaId, nome: disciplinaOptions.find((d) => d.id === disciplinaId)?.label ?? "" }
    : null;

  const handleNext = async () => {
    const fieldKey = ["professor_id", "turma_id", "disciplina_id"][step] as keyof AllocationFormData;
    const valid = await trigger(fieldKey);
    if (!valid) return;
    setStep((s) => s + 1);
  };

  const renderProfessorList = () => filteredProfessores.map((p) => {
    const nome = (p as any).nome || p.usuario_id.slice(0, 8);
    return (
      <button
        key={p.usuario_id}
        type="button"
        className={`w-full text-left px-3 py-2.5 text-sm rounded-lg transition-colors ${
          professorId === p.usuario_id
            ? "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400"
            : "hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
        }`}
        onClick={() => {
          setValue("professor_id", p.usuario_id, { shouldValidate: true });
          setSearch(nome);
        }}
      >
        <span className="font-medium">{nome}</span>
        {p.formacao_principal && (
          <span className="ml-2 text-xs text-gray-400">— {p.formacao_principal}</span>
        )}
      </button>
    );
  });

  const onSubmit = (data: AllocationFormData) => createMutation.mutate(data);

  return (
    <div className="max-w-2xl mx-auto">
      <Breadcrumb items={[{ label: "Alocações", path: `${prefix}/alocacoes` }, { label: "Nova Alocação" }]} />

      <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Nova Alocação</h1>

      <StepIndicator steps={steps.map((s) => ({ label: s }))} currentStep={step} />

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div ref={formTopRef} tabIndex={-1} className="outline-none" />
          <input type="hidden" name="professor_id" value={professorId} readOnly />
          <input type="hidden" name="turma_id" value={turmaId} readOnly />
          <input type="hidden" name="disciplina_id" value={disciplinaId} readOnly />
          <input type="hidden" name="data_inicio" value={dataInicio} readOnly />

          <div ref={errorRef}>
            {step === 0 && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    aria-label="Buscar professor por nome"
                    aria-invalid={errors.professor_id ? "true" : undefined}
                    aria-describedby={errors.professor_id ? "professor-error" : undefined}
                    className="w-full pl-9 pr-3 py-2.5 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
                    placeholder="Digite o nome do professor..."
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      setValue("professor_id", "", { shouldValidate: false });
                    }}
                    autoFocus
                  />
                </div>

                {errors.professor_id && (
                  <p id="professor-error" className="text-xs text-danger-500" role="alert">{errors.professor_id.message}</p>
                )}

                {selectedProfessor && (
                  <div className="flex items-center gap-3 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
                    <UserCheck className="h-5 w-5 text-success-500" />
                    <span className="text-sm font-medium text-success-700 dark:text-success-400">
                      Professor selecionado: {selectedProfessor.nome}
                    </span>
                  </div>
                )}

                {search && !selectedProfessor && (
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {loadingTeachers && (
                      <p className="text-sm text-gray-400 text-center py-4">Buscando...</p>
                    )}
                    {!loadingTeachers && filteredProfessores.length === 0 && (
                      <p className="text-sm text-gray-400 text-center py-4">Nenhum professor encontrado</p>
                    )}
                    {renderProfessorList()}
                  </div>
                )}
              </div>
            )}

            {step === 1 && (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {turmaOptions.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-4">Nenhuma turma disponível</p>
                )}
                {turmaOptions.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                      turmaId === t.id
                        ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400"
                        : "border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 text-gray-700 dark:text-gray-300"
                    }`}
                    onClick={() => setValue("turma_id", t.id, { shouldValidate: true })}
                  >
                    <div className="flex items-center gap-3">
                      <School className="h-5 w-5 text-gray-400" />
                      <div>
                        <p className="font-medium">{t.label}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {step === 2 && (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {disciplinaOptions.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-4">Nenhuma disciplina disponível</p>
                )}
                {disciplinaOptions.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    className={`w-full text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                      disciplinaId === d.id
                        ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400"
                        : "border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 text-gray-700 dark:text-gray-300"
                    }`}
                    onClick={() => setValue("disciplina_id", d.id, { shouldValidate: true })}
                  >
                    <div className="flex items-center gap-3">
                      <BookOpen className="h-5 w-5 text-gray-400" />
                      <div>
                        <p className="font-medium">{d.label}</p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <UserCheck className="h-5 w-5 text-primary-500" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Professor</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedProfessor?.nome}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <School className="h-5 w-5 text-primary-500" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Turma</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedTurma?.label}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <BookOpen className="h-5 w-5 text-primary-500" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Disciplina</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedDisciplina?.nome}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-primary-500" />
                    Data de Início
                  </label>
                  <input
                    type="date"
                    className={`w-full px-3 py-2.5 text-sm bg-transparent border rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-0 dark:text-gray-100 ${
                      errors.data_inicio
                        ? "border-danger-500 focus:ring-danger-500"
                        : "border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500"
                    }`}
                    value={dataInicio}
                    onChange={(e) => setValue("data_inicio", e.target.value, { shouldValidate: true })}
                  />
                  {errors.data_inicio && (
                    <p className="text-xs text-danger-500">{errors.data_inicio.message}</p>
                  )}
                </div>

                {(errors.professor_id || errors.turma_id || errors.disciplina_id) && (
                  <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-danger-500" />
                    <span className="text-sm text-danger-600 dark:text-danger-400">
                      {errors.professor_id?.message || errors.turma_id?.message || errors.disciplina_id?.message}
                    </span>
                  </div>
                )}

                {createMutation.isError && (
                  <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-danger-500" />
                    <span className="text-sm text-danger-600 dark:text-danger-400">
                      {(createMutation.error as any)?.response?.data?.message || "Erro ao criar alocação"}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
            <Button
              variant="ghost"
              type="button"
              onClick={() => {
                if (step === 0) navigate(`${prefix}/alocacoes`);
                else setStep((s) => s - 1);
              }}
            >
              {step === 0 ? "Cancelar" : "Voltar"}
            </Button>

            {step < 3 ? (
              <Button type="button" onClick={handleNext}>
                Próximo
              </Button>
            ) : (
              <Button type="submit" loading={isSubmitting || createMutation.isPending}>
                Criar Alocação
              </Button>
            )}
          </div>
        </form>
      </Card>
    </div>
  );
}
