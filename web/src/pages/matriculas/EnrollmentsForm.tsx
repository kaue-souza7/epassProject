import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { enrollmentsApi, studentsApi, classesApi, seriesApi, academicYearsApi } from "../../api/endpoints";
import type { Aluno } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { StepIndicator } from "../../components/ui/StepIndicator";
import { Search, UserCheck, School, AlertCircle } from "lucide-react";

const enrollmentSchema = z.object({
  aluno_id: z.string().min(1, "Selecione um aluno"),
  turma_id: z.string().min(1, "Selecione uma turma"),
});

type EnrollmentFormData = z.infer<typeof enrollmentSchema>;

const steps = ["Selecionar Aluno", "Selecionar Turma", "Confirmar"];

export function EnrollmentsForm() {
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
  } = useForm<EnrollmentFormData>({
    resolver: zodResolver(enrollmentSchema),
    defaultValues: { aluno_id: "", turma_id: "" },
  });

  const alunoId = watch("aluno_id");
  const turmaId = watch("turma_id");

  const [step, setStep] = useState(0);
  const [search, setSearch] = useState("");

  const formTopRef = useRef<HTMLDivElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    formTopRef.current?.focus();
  }, [step]);

  const { data: studentsAlunos, isLoading: loadingStudents } = useQuery({
    queryKey: ["students", { nome: search }],
    queryFn: () => studentsApi.list({ nome: search || undefined }),
    enabled: step === 0,
  });

  const { data: classes } = useQuery({
    queryKey: ["classes"],
    queryFn: () => classesApi.list(),
    enabled: step >= 1,
  });

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
  });

  const { data: anosLetivos } = useQuery({
    queryKey: ["academic-years"],
    queryFn: () => academicYearsApi.list(),
  });

  const serieMap = new Map(series?.map((s) => [s.id, s]) ?? []);
  const anoMap = new Map(anosLetivos?.map((a) => [a.id, a]) ?? []);

  const turmaOptions = (classes?.items ?? [])
    .filter((t) => t.ativo)
    .map((t) => {
      const serie = serieMap.get(t.serie_id);
      return {
        id: t.id,
        label: `${t.codigo} — ${serie?.nome ?? "?"} (${anoMap.get(t.ano_letivo_id)?.ano ?? "?"}) — ${t.vagas_total} vagas`,
        vagas: t.vagas_total,
      };
    });

  const createMutation = useMutation({
    mutationFn: (data: EnrollmentFormData) => enrollmentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["enrollments"] });
      toast("success", "Matrícula realizada com sucesso");
      navigate(`${prefix}/matriculas`);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao realizar matrícula");
    },
  });

  useEffect(() => {
    if (errors.aluno_id || errors.turma_id) {
      errorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [errors]);

  const selectedAluno = alunoId
    ? { id: alunoId, nome: studentsAlunos?.items?.find((a) => a.id === alunoId)?.nome ?? "" }
    : null;

  const selectedTurma = turmaId
    ? { id: turmaId, label: turmaOptions.find((t) => t.id === turmaId)?.label ?? "" }
    : null;

  const canGoNext = step === 0 ? !!alunoId : true;

  const handleNext = async () => {
    if (step === 0) {
      const valid = await trigger("aluno_id");
      if (!valid) return;
    }
    setStep((s) => s + 1);
  };

  const renderStudentList = (alunos: Aluno[] | undefined) => alunos?.map((a) => (
    <button
      key={a.id}
      type="button"
      className={`w-full text-left px-3 py-2.5 text-sm rounded-lg transition-colors ${
        alunoId === a.id
          ? "bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400"
          : "hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
      }`}
      onClick={() => {
        setValue("aluno_id", a.id, { shouldValidate: true });
        setSearch(a.nome);
      }}
    >
      {a.nome}
    </button>
  ));

  const onSubmit = (data: EnrollmentFormData) => createMutation.mutate(data);

  return (
    <div className="max-w-2xl mx-auto">
      <Breadcrumb items={[{ label: "Matrículas", path: `${prefix}/matriculas` }, { label: "Nova Matrícula" }]} />

      <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Nova Matrícula</h1>

      <StepIndicator steps={steps.map((s) => ({ label: s }))} currentStep={step} />

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div ref={formTopRef} tabIndex={-1} className="outline-none" />
          <input type="hidden" {...{ name: "aluno_id", value: alunoId }} />
          <input type="hidden" {...{ name: "turma_id", value: turmaId }} />

          <div ref={errorRef}>
            {step === 0 && (
              <div className="space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    aria-label="Buscar aluno por nome"
                    aria-invalid={errors.aluno_id ? "true" : undefined}
                    aria-describedby={errors.aluno_id ? "aluno-error" : undefined}
                    className="w-full pl-9 pr-3 py-2.5 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
                    placeholder="Digite o nome do aluno..."
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      setValue("aluno_id", "", { shouldValidate: false });
                    }}
                    autoFocus
                  />
                </div>

                {errors.aluno_id && (
                  <p id="aluno-error" className="text-xs text-danger-500" role="alert">{errors.aluno_id.message}</p>
                )}

                {selectedAluno && (
                  <div className="flex items-center gap-3 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
                    <UserCheck className="h-5 w-5 text-success-500" />
                    <span className="text-sm font-medium text-success-700 dark:text-success-400">
                      Aluno selecionado: {selectedAluno.nome}
                    </span>
                  </div>
                )}

                {search && !selectedAluno && (
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {loadingStudents && (
                      <p className="text-sm text-gray-400 text-center py-4">Buscando...</p>
                    )}
                    {!loadingStudents && (!studentsAlunos?.items || studentsAlunos.items.length === 0) && (
                      <p className="text-sm text-gray-400 text-center py-4">Nenhum aluno encontrado</p>
                    )}
                    {renderStudentList(studentsAlunos?.items)}
                  </div>
                )}
              </div>
            )}

            {/* Step 1: Select Class */}
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

            {/* Step 2: Confirm */}
            {step === 2 && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <UserCheck className="h-5 w-5 text-primary-500" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Aluno</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedAluno?.nome}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <School className="h-5 w-5 text-primary-500" />
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Turma</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedTurma?.label}</p>
                  </div>
                </div>

                {(errors.aluno_id || errors.turma_id) && (
                  <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-danger-500" />
                    <span className="text-sm text-danger-600 dark:text-danger-400">
                      {errors.aluno_id?.message || errors.turma_id?.message}
                    </span>
                  </div>
                )}

                {createMutation.isError && (
                  <div className="flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-lg">
                    <AlertCircle className="h-5 w-5 text-danger-500" />
                    <span className="text-sm text-danger-600 dark:text-danger-400">
                      {(createMutation.error as any)?.response?.data?.message || "Erro ao realizar matrícula"}
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
                if (step === 0) navigate(`${prefix}/matriculas`);
                else setStep((s) => s - 1);
              }}
            >
              {step === 0 ? "Cancelar" : "Voltar"}
            </Button>

            {step < 2 ? (
              <Button type="button" onClick={handleNext} disabled={!canGoNext}>
                Próximo
              </Button>
            ) : (
              <Button type="submit" loading={isSubmitting || createMutation.isPending}>
                Confirmar Matrícula
              </Button>
            )}
          </div>
        </form>
      </Card>
    </div>
  );
}
