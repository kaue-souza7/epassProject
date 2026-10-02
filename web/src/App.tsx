import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthLayout } from "./layouts/AuthLayout";
import { RootLayout } from "./layouts/RootLayout";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Login } from "./pages/Login";
import { AdminDashboard } from "./pages/dashboard/AdminDashboard";
import { SecretariaDashboard } from "./pages/dashboard/SecretariaDashboard";
import { ProfessorDashboard } from "./pages/dashboard/ProfessorDashboard";
import { ResponsavelDashboard } from "./pages/dashboard/ResponsavelDashboard";
import { Unauthorized } from "./pages/Unauthorized";
import { NotFound } from "./pages/NotFound";
import { AnosLetivosList } from "./pages/anos-letivos/AnosLetivosList";
import { AnosLetivosForm } from "./pages/anos-letivos/AnosLetivosForm";
import { SeriesList } from "./pages/series/SeriesList";
import { SeriesForm } from "./pages/series/SeriesForm";
import { DisciplinasList } from "./pages/disciplinas/DisciplinasList";
import { DisciplinasForm } from "./pages/disciplinas/DisciplinasForm";
import { ProfessoresList } from "./pages/professores/ProfessoresList";
import { ProfessoresForm } from "./pages/professores/ProfessoresForm";
import { AlunosList } from "./pages/alunos/AlunosList";
import { AlunosForm } from "./pages/alunos/AlunosForm";
import { TurmasList } from "./pages/turmas/TurmasList";
import { TurmasForm } from "./pages/turmas/TurmasForm";
import { EnrollmentsList } from "./pages/matriculas/EnrollmentsList";
import { EnrollmentsForm } from "./pages/matriculas/EnrollmentsForm";
import { EnrollmentDetail } from "./pages/matriculas/EnrollmentDetail";
import { AllocationsList } from "./pages/alocacoes/AllocationsList";
import { AllocationsForm } from "./pages/alocacoes/AllocationsForm";
import { AllocationDetail } from "./pages/alocacoes/AllocationDetail";
import { GradeHorariaPage } from "./pages/grade/GradeHorariaPage";
import { MyClasses } from "./pages/professor/MyClasses";
import { CallsList } from "./pages/professor/CallsList";
import { CallForm } from "./pages/professor/CallForm";
import { FrequencyRegister } from "./pages/professor/FrequencyRegister";
import { AssessmentsList } from "./pages/professor/AssessmentsList";
import { AssessmentForm } from "./pages/professor/AssessmentForm";
import { AssessmentGrades } from "./pages/professor/AssessmentGrades";
import { ProfessorReportCards } from "./pages/professor/ProfessorReportCards";
import { AtenaChat } from "./pages/atena/AtenaChat";
import { MyChildren } from "./pages/responsavel/MyChildren";
import { ChildDetails } from "./pages/responsavel/ChildDetails";
import { ReportCard } from "./pages/responsavel/ReportCard";
import { AcademicConfigPage } from "./pages/admin/AcademicConfigPage";
import { StudentHistory } from "./pages/students/StudentHistory";
import { AgendaPage } from "./pages/agenda/AgendaPage";
import { EventForm } from "./pages/agenda/EventForm";
import { EventDetail } from "./pages/agenda/EventDetail";
import { CantinaConfigPage } from "./pages/cantina/CantinaConfigPage";
import { GestaoPage } from "./pages/cantina/GestaoPage";
import { CadastroPage } from "./pages/cantina/CadastroPage";
import { KanbanPage } from "./pages/cantina/KanbanPage";
import { AtendimentoPage } from "./pages/cantina/AtendimentoPage";
import { CarteirasPage } from "./pages/financeiro/CarteirasPage";
import { AvisosPage } from "./pages/comunicacao/AvisosPage";
import { OcorrenciasPage } from "./pages/comunicacao/OcorrenciasPage";
import { NotificacoesPage } from "./pages/comunicacao/NotificacoesPage";
import { RealtimeProvider } from "./contexts/RealtimeContext";
import { useAuth } from "./contexts/AuthContext";

const DASHBOARD_POR_PERFIL: Record<string, string> = {
  admin: "/admin/dashboard",
  secretaria: "/secretaria/dashboard",
  professor: "/professor/dashboard",
  responsavel: "/responsavel/dashboard",
  cantineiro: "/cantineiro/cantina/gestao",
  coordenador: "/coordenador/avisos",
};

function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={DASHBOARD_POR_PERFIL[user.perfil] ?? "/login"} replace />;
}

function role(roles: string[], element: React.ReactNode) {
  return <ProtectedRoute requiredRoles={roles}>{element}</ProtectedRoute>;
}

export function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
      <RealtimeProvider>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>

        <Route path="/403" element={<Unauthorized />} />
        <Route path="/404" element={<NotFound />} />

        <Route element={<ProtectedRoute><RootLayout /></ProtectedRoute>}>
          {/* Dashboards */}
          <Route path="/admin/dashboard" element={role(["admin"], <AdminDashboard />)} />
          <Route path="/secretaria/dashboard" element={role(["secretaria"], <SecretariaDashboard />)} />
          <Route path="/professor/dashboard" element={role(["professor"], <ProfessorDashboard />)} />
          <Route path="/responsavel/dashboard" element={role(["responsavel"], <ResponsavelDashboard />)} />

          {/* Admin — Anos Letivos */}
          <Route path="/admin/anos-letivos" element={role(["admin"], <AnosLetivosList />)} />
          <Route path="/admin/anos-letivos/novo" element={role(["admin"], <AnosLetivosForm />)} />
          <Route path="/admin/anos-letivos/:id" element={role(["admin"], <AnosLetivosForm />)} />

          {/* Admin — Séries */}
          <Route path="/admin/series" element={role(["admin"], <SeriesList />)} />
          <Route path="/admin/series/novo" element={role(["admin"], <SeriesForm />)} />
          <Route path="/admin/series/:id" element={role(["admin"], <SeriesForm />)} />

          {/* Admin — Disciplinas */}
          <Route path="/admin/disciplinas" element={role(["admin"], <DisciplinasList />)} />
          <Route path="/admin/disciplinas/novo" element={role(["admin"], <DisciplinasForm />)} />
          <Route path="/admin/disciplinas/:id" element={role(["admin"], <DisciplinasForm />)} />

          {/* Admin — Professores */}
          <Route path="/admin/professores" element={role(["admin", "secretaria"], <ProfessoresList />)} />
          <Route path="/admin/professores/novo" element={role(["admin", "secretaria"], <ProfessoresForm />)} />
          <Route path="/admin/professores/:id" element={role(["admin", "secretaria"], <ProfessoresForm />)} />

          {/* Admin — Alunos */}
          <Route path="/admin/alunos" element={role(["admin", "secretaria"], <AlunosList />)} />
          <Route path="/admin/alunos/novo" element={role(["admin", "secretaria"], <AlunosForm />)} />
          <Route path="/admin/alunos/:id" element={role(["admin", "secretaria"], <AlunosForm />)} />

          {/* Admin — Turmas */}
          <Route path="/admin/turmas" element={role(["admin", "secretaria"], <TurmasList />)} />
          <Route path="/admin/turmas/novo" element={role(["admin", "secretaria"], <TurmasForm />)} />
          <Route path="/admin/turmas/:id" element={role(["admin", "secretaria"], <TurmasForm />)} />

          {/* Secretaria — Anos Letivos (read-only) */}
          <Route path="/secretaria/anos-letivos" element={role(["secretaria"], <AnosLetivosList />)} />
          <Route path="/secretaria/anos-letivos/:id" element={role(["secretaria"], <AnosLetivosForm />)} />

          {/* Secretaria — Séries (read-only) */}
          <Route path="/secretaria/series" element={role(["secretaria"], <SeriesList />)} />
          <Route path="/secretaria/series/:id" element={role(["secretaria"], <SeriesForm />)} />

          {/* Secretaria — Disciplinas (read-only) */}
          <Route path="/secretaria/disciplinas" element={role(["secretaria"], <DisciplinasList />)} />
          <Route path="/secretaria/disciplinas/:id" element={role(["secretaria"], <DisciplinasForm />)} />

          {/* Secretaria — Professores */}
          <Route path="/secretaria/professores" element={role(["secretaria"], <ProfessoresList />)} />
          <Route path="/secretaria/professores/novo" element={role(["secretaria"], <ProfessoresForm />)} />
          <Route path="/secretaria/professores/:id" element={role(["secretaria"], <ProfessoresForm />)} />

          {/* Secretaria — Alunos */}
          <Route path="/secretaria/alunos" element={role(["secretaria"], <AlunosList />)} />
          <Route path="/secretaria/alunos/novo" element={role(["secretaria"], <AlunosForm />)} />
          <Route path="/secretaria/alunos/:id" element={role(["secretaria"], <AlunosForm />)} />

          {/* Secretaria — Turmas */}
          <Route path="/secretaria/turmas" element={role(["secretaria"], <TurmasList />)} />
          <Route path="/secretaria/turmas/novo" element={role(["secretaria"], <TurmasForm />)} />
          <Route path="/secretaria/turmas/:id" element={role(["secretaria"], <TurmasForm />)} />

          {/* Admin — Matrículas */}
          <Route path="/admin/matriculas" element={role(["admin", "secretaria"], <EnrollmentsList />)} />
          <Route path="/admin/matriculas/novo" element={role(["admin", "secretaria"], <EnrollmentsForm />)} />
          <Route path="/admin/matriculas/:id" element={role(["admin", "secretaria"], <EnrollmentDetail />)} />

          {/* Secretaria — Matrículas */}
          <Route path="/secretaria/matriculas" element={role(["secretaria"], <EnrollmentsList />)} />
          <Route path="/secretaria/matriculas/novo" element={role(["secretaria"], <EnrollmentsForm />)} />
          <Route path="/secretaria/matriculas/:id" element={role(["secretaria"], <EnrollmentDetail />)} />

          {/* Admin — Histórico Escolar */}
          <Route path="/admin/alunos/:id/historico" element={role(["admin", "secretaria"], <StudentHistory />)} />

          {/* Secretaria — Histórico Escolar */}
          <Route path="/secretaria/alunos/:id/historico" element={role(["secretaria"], <StudentHistory />)} />

          {/* Admin — Configurações Acadêmicas */}
          <Route path="/admin/configuracoes-academicas" element={role(["admin"], <AcademicConfigPage />)} />

          {/* Admin — Alocações */}
          <Route path="/admin/alocacoes" element={role(["admin"], <AllocationsList />)} />
          <Route path="/admin/alocacoes/novo" element={role(["admin"], <AllocationsForm />)} />
          <Route path="/admin/alocacoes/:id" element={role(["admin"], <AllocationDetail />)} />

          {/* Secretaria — Alocações */}
          <Route path="/secretaria/alocacoes" element={role(["secretaria"], <AllocationsList />)} />
          <Route path="/secretaria/alocacoes/:id" element={role(["secretaria"], <AllocationDetail />)} />

          {/* Grade horária — Admin e Secretaria */}
          <Route path="/admin/grade-horaria" element={role(["admin"], <GradeHorariaPage />)} />
          <Route path="/secretaria/grade-horaria" element={role(["secretaria"], <GradeHorariaPage />)} />

          {/* Agenda — Admin */}
          <Route path="/admin/agenda" element={role(["admin"], <AgendaPage />)} />
          <Route path="/admin/agenda/eventos/novo" element={role(["admin"], <EventForm />)} />
          <Route path="/admin/agenda/eventos/:id" element={role(["admin"], <EventDetail />)} />
          <Route path="/admin/agenda/eventos/:id/editar" element={role(["admin"], <EventForm />)} />

          {/* Agenda — Secretaria */}
          <Route path="/secretaria/agenda" element={role(["secretaria"], <AgendaPage />)} />
          <Route path="/secretaria/agenda/eventos/novo" element={role(["secretaria"], <EventForm />)} />
          <Route path="/secretaria/agenda/eventos/:id" element={role(["secretaria"], <EventDetail />)} />
          <Route path="/secretaria/agenda/eventos/:id/editar" element={role(["secretaria"], <EventForm />)} />

          {/* Agenda — Professor */}
          <Route path="/professor/agenda" element={role(["professor"], <AgendaPage />)} />
          <Route path="/professor/agenda/eventos/novo" element={role(["professor"], <EventForm />)} />
          <Route path="/professor/agenda/eventos/:id" element={role(["professor"], <EventDetail />)} />
          <Route path="/professor/agenda/eventos/:id/editar" element={role(["professor"], <EventForm />)} />

          {/* Agenda — Responsável */}
          <Route path="/responsavel/agenda" element={role(["responsavel"], <AgendaPage />)} />
          <Route path="/responsavel/agenda/eventos/:id" element={role(["responsavel"], <EventDetail />)} />

          {/* Responsável — Portal */}
          <Route path="/responsavel/meus-filhos" element={role(["responsavel"], <MyChildren />)} />
          <Route path="/responsavel/meus-filhos/:childId" element={role(["responsavel"], <ChildDetails />)} />
          <Route path="/responsavel/meus-filhos/:childId/boletim/:enrollmentId" element={role(["responsavel"], <ReportCard />)} />

          {/* Atena — o mesmo componente para todos os perfis. O escopo de
              dados é resolvido no backend pela allowlist por perfil, então a
              tela não precisa de uma variante por papel: só muda o que ela
              mostra em volta (o seletor de filho existe só para o
              responsável). */}
          <Route path="/responsavel/atena" element={role(["responsavel"], <AtenaChat />)} />
          <Route path="/professor/atena" element={role(["professor"], <AtenaChat />)} />
          <Route path="/secretaria/atena" element={role(["secretaria"], <AtenaChat />)} />
          <Route path="/admin/atena" element={role(["admin"], <AtenaChat />)} />
          <Route path="/coordenador/atena" element={role(["coordenador"], <AtenaChat />)} />
          <Route path="/cantineiro/atena" element={role(["cantineiro"], <AtenaChat />)} />

          {/* Professor — Minhas Turmas */}
          <Route path="/professor/minhas-turmas" element={role(["professor"], <MyClasses />)} />
          <Route path="/professor/chamadas" element={<Navigate to="/professor/minhas-turmas" replace />} />
          <Route path="/professor/frequencias" element={<Navigate to="/professor/minhas-turmas" replace />} />
          <Route path="/professor/avaliacoes" element={<Navigate to="/professor/minhas-turmas" replace />} />
          <Route path="/professor/turma/:alocacaoId/chamadas" element={role(["professor"], <CallsList />)} />
          <Route path="/professor/turma/:alocacaoId/chamada/nova" element={role(["professor"], <CallForm />)} />
          <Route path="/professor/chamada/:callId" element={role(["professor"], <FrequencyRegister />)} />
          <Route path="/professor/turma/:alocacaoId/avaliacoes" element={role(["professor"], <AssessmentsList />)} />
          <Route path="/professor/turma/:alocacaoId/avaliacao/nova" element={role(["professor"], <AssessmentForm />)} />
          <Route path="/professor/avaliacao/:assessmentId/notas" element={role(["professor"], <AssessmentGrades />)} />
          {/* Cantineiro — Dashboard (redirect para gestao) */}
          <Route path="/cantineiro/dashboard" element={<Navigate to="/cantineiro/cantina/gestao" replace />} />

          {/* Financeiro — Carteiras (admin) */}
          <Route path="/admin/carteiras" element={role(["admin"], <CarteirasPage />)} />

          {/* Cantina — Admin (telas principais) */}
          <Route path="/admin/cantina/gestao" element={role(["admin"], <GestaoPage />)} />
          <Route path="/admin/cantina/atendimento" element={role(["admin"], <AtendimentoPage />)} />
          <Route path="/admin/cantina/cadastro" element={role(["admin"], <CadastroPage />)} />
          <Route path="/admin/cantina/kanban" element={role(["admin"], <KanbanPage />)} />
          <Route path="/admin/cantina-config" element={role(["admin"], <CantinaConfigPage />)} />

          {/* Cantina — Cantineiro (telas principais) */}
          <Route path="/cantineiro/cantina/gestao" element={role(["admin", "cantineiro"], <GestaoPage />)} />
          <Route path="/cantineiro/cantina/atendimento" element={role(["admin", "cantineiro"], <AtendimentoPage />)} />
          <Route path="/cantineiro/cantina/cadastro" element={role(["admin", "cantineiro"], <CadastroPage />)} />
          <Route path="/cantineiro/cantina/kanban" element={role(["admin", "cantineiro"], <KanbanPage />)} />

          {/* Professor — Boletins */}
          <Route path="/professor/boletins" element={role(["professor"], <ProfessorReportCards />)} />
          <Route path="/professor/boletins/:enrollmentId" element={role(["professor"], <ReportCard />)} />
          <Route path="/professor/turma/:turmaId/boletins" element={role(["professor"], <ProfessorReportCards />)} />

          {/* Comunicação — Avisos / Ocorrências / Notificações */}
          {(
            [
              ["admin", ["admin"]],
              ["secretaria", ["secretaria"]],
              ["coordenador", ["coordenador"]],
            ] as const
          ).map(([prefix, roles]) => (
            <Route key={`${prefix}-avisos`} path={`/${prefix}/avisos`} element={role([...roles], <AvisosPage />)} />
          ))}
          {(
            [
              ["admin", ["admin"]],
              ["secretaria", ["secretaria"]],
              ["coordenador", ["coordenador"]],
            ] as const
          ).map(([prefix, roles]) => (
            <Route key={`${prefix}-ocorrencias`} path={`/${prefix}/ocorrencias`} element={role([...roles], <OcorrenciasPage />)} />
          ))}
          {(
            [
              ["admin", ["admin"]],
              ["secretaria", ["secretaria"]],
              ["coordenador", ["coordenador"]],
              ["professor", ["professor"]],
              ["cantineiro", ["cantineiro"]],
            ] as const
          ).map(([prefix, roles]) => (
            <Route key={`${prefix}-notificacoes`} path={`/${prefix}/notificacoes`} element={role([...roles], <NotificacoesPage />)} />
          ))}
          <Route path="/responsavel/avisos" element={role(["responsavel"], <AvisosPage />)} />
          <Route path="/responsavel/ocorrencias" element={role(["responsavel"], <OcorrenciasPage />)} />
          <Route path="/responsavel/notificacoes" element={role(["responsavel"], <NotificacoesPage />)} />
          <Route path="/professor/ocorrencias" element={role(["professor"], <OcorrenciasPage />)} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
      </RealtimeProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}