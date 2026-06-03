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
import { MyClasses } from "./pages/professor/MyClasses";
import { CallsList } from "./pages/professor/CallsList";
import { CallForm } from "./pages/professor/CallForm";
import { FrequencyRegister } from "./pages/professor/FrequencyRegister";
import { AssessmentsList } from "./pages/professor/AssessmentsList";
import { AssessmentForm } from "./pages/professor/AssessmentForm";
import { AssessmentGrades } from "./pages/professor/AssessmentGrades";
import { ProfessorReportCards } from "./pages/professor/ProfessorReportCards";
import { MyChildren } from "./pages/responsavel/MyChildren";
import { ChildDetails } from "./pages/responsavel/ChildDetails";
import { ReportCard } from "./pages/responsavel/ReportCard";
import { AcademicConfigPage } from "./pages/admin/AcademicConfigPage";
import { StudentHistory } from "./pages/students/StudentHistory";
import { AgendaPage } from "./pages/agenda/AgendaPage";
import { EventForm } from "./pages/agenda/EventForm";
import { EventDetail } from "./pages/agenda/EventDetail";
import { useAuth } from "./contexts/AuthContext";

function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={`/${user.perfil}/dashboard`} replace />;
}

export function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
      <Routes>
        <Route path="/" element={<HomeRedirect />} />

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
        </Route>

        <Route path="/403" element={<Unauthorized />} />
        <Route path="/404" element={<NotFound />} />

        <Route element={<ProtectedRoute><RootLayout /></ProtectedRoute>}>
          {/* Dashboards */}
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/secretaria/dashboard" element={<SecretariaDashboard />} />
          <Route path="/professor/dashboard" element={<ProfessorDashboard />} />
          <Route path="/responsavel/dashboard" element={<ResponsavelDashboard />} />

          {/* Admin — Anos Letivos */}
          <Route path="/admin/anos-letivos" element={<AnosLetivosList />} />
          <Route path="/admin/anos-letivos/novo" element={<ProtectedRoute requiredRoles={["admin"]}><AnosLetivosForm /></ProtectedRoute>} />
          <Route path="/admin/anos-letivos/:id" element={<AnosLetivosForm />} />

          {/* Admin — Séries */}
          <Route path="/admin/series" element={<SeriesList />} />
          <Route path="/admin/series/novo" element={<ProtectedRoute requiredRoles={["admin"]}><SeriesForm /></ProtectedRoute>} />
          <Route path="/admin/series/:id" element={<SeriesForm />} />

          {/* Admin — Disciplinas */}
          <Route path="/admin/disciplinas" element={<DisciplinasList />} />
          <Route path="/admin/disciplinas/novo" element={<ProtectedRoute requiredRoles={["admin"]}><DisciplinasForm /></ProtectedRoute>} />
          <Route path="/admin/disciplinas/:id" element={<DisciplinasForm />} />

          {/* Admin — Professores */}
          <Route path="/admin/professores" element={<ProfessoresList />} />
          <Route path="/admin/professores/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><ProfessoresForm /></ProtectedRoute>} />
          <Route path="/admin/professores/:id" element={<ProfessoresForm />} />

          {/* Admin — Alunos */}
          <Route path="/admin/alunos" element={<AlunosList />} />
          <Route path="/admin/alunos/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><AlunosForm /></ProtectedRoute>} />
          <Route path="/admin/alunos/:id" element={<AlunosForm />} />

          {/* Admin — Turmas */}
          <Route path="/admin/turmas" element={<TurmasList />} />
          <Route path="/admin/turmas/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><TurmasForm /></ProtectedRoute>} />
          <Route path="/admin/turmas/:id" element={<TurmasForm />} />

          {/* Secretaria — Anos Letivos (read-only) */}
          <Route path="/secretaria/anos-letivos" element={<AnosLetivosList />} />
          <Route path="/secretaria/anos-letivos/:id" element={<AnosLetivosForm />} />

          {/* Secretaria — Séries (read-only) */}
          <Route path="/secretaria/series" element={<SeriesList />} />
          <Route path="/secretaria/series/:id" element={<SeriesForm />} />

          {/* Secretaria — Disciplinas (read-only) */}
          <Route path="/secretaria/disciplinas" element={<DisciplinasList />} />
          <Route path="/secretaria/disciplinas/:id" element={<DisciplinasForm />} />

          {/* Secretaria — Professores */}
          <Route path="/secretaria/professores" element={<ProfessoresList />} />
          <Route path="/secretaria/professores/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><ProfessoresForm /></ProtectedRoute>} />
          <Route path="/secretaria/professores/:id" element={<ProfessoresForm />} />

          {/* Secretaria — Alunos */}
          <Route path="/secretaria/alunos" element={<AlunosList />} />
          <Route path="/secretaria/alunos/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><AlunosForm /></ProtectedRoute>} />
          <Route path="/secretaria/alunos/:id" element={<AlunosForm />} />

          {/* Secretaria — Turmas */}
          <Route path="/secretaria/turmas" element={<TurmasList />} />
          <Route path="/secretaria/turmas/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><TurmasForm /></ProtectedRoute>} />
          <Route path="/secretaria/turmas/:id" element={<TurmasForm />} />

          {/* Admin — Matrículas */}
          <Route path="/admin/matriculas" element={<EnrollmentsList />} />
          <Route path="/admin/matriculas/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><EnrollmentsForm /></ProtectedRoute>} />
          <Route path="/admin/matriculas/:id" element={<EnrollmentDetail />} />

          {/* Secretaria — Matrículas */}
          <Route path="/secretaria/matriculas" element={<EnrollmentsList />} />
          <Route path="/secretaria/matriculas/novo" element={<ProtectedRoute requiredRoles={["admin", "secretaria"]}><EnrollmentsForm /></ProtectedRoute>} />
          <Route path="/secretaria/matriculas/:id" element={<EnrollmentDetail />} />

          {/* Admin — Histórico Escolar */}
          <Route path="/admin/alunos/:id/historico" element={<StudentHistory />} />

          {/* Secretaria — Histórico Escolar */}
          <Route path="/secretaria/alunos/:id/historico" element={<StudentHistory />} />

          {/* Admin — Configurações Acadêmicas */}
          <Route path="/admin/configuracoes-academicas" element={<ProtectedRoute requiredRoles={["admin"]}><AcademicConfigPage /></ProtectedRoute>} />

          {/* Admin — Alocações */}
          <Route path="/admin/alocacoes" element={<AllocationsList />} />
          <Route path="/admin/alocacoes/novo" element={<ProtectedRoute requiredRoles={["admin"]}><AllocationsForm /></ProtectedRoute>} />
          <Route path="/admin/alocacoes/:id" element={<AllocationDetail />} />

          {/* Secretaria — Alocações */}
          <Route path="/secretaria/alocacoes" element={<AllocationsList />} />
          <Route path="/secretaria/alocacoes/:id" element={<AllocationDetail />} />

          {/* Agenda — Admin */}
          <Route path="/admin/agenda" element={<AgendaPage />} />
          <Route path="/admin/agenda/eventos/novo" element={<ProtectedRoute requiredRoles={["admin"]}><EventForm /></ProtectedRoute>} />
          <Route path="/admin/agenda/eventos/:id" element={<EventDetail />} />
          <Route path="/admin/agenda/eventos/:id/editar" element={<ProtectedRoute requiredRoles={["admin"]}><EventForm /></ProtectedRoute>} />

          {/* Agenda — Secretaria */}
          <Route path="/secretaria/agenda" element={<AgendaPage />} />
          <Route path="/secretaria/agenda/eventos/novo" element={<ProtectedRoute requiredRoles={["secretaria"]}><EventForm /></ProtectedRoute>} />
          <Route path="/secretaria/agenda/eventos/:id" element={<EventDetail />} />
          <Route path="/secretaria/agenda/eventos/:id/editar" element={<ProtectedRoute requiredRoles={["secretaria"]}><EventForm /></ProtectedRoute>} />

          {/* Agenda — Professor */}
          <Route path="/professor/agenda" element={<AgendaPage />} />
          <Route path="/professor/agenda/eventos/novo" element={<ProtectedRoute requiredRoles={["professor"]}><EventForm /></ProtectedRoute>} />
          <Route path="/professor/agenda/eventos/:id" element={<EventDetail />} />
          <Route path="/professor/agenda/eventos/:id/editar" element={<ProtectedRoute requiredRoles={["professor"]}><EventForm /></ProtectedRoute>} />

          {/* Agenda — Responsável */}
          <Route path="/responsavel/agenda" element={<AgendaPage />} />
          <Route path="/responsavel/agenda/eventos/:id" element={<EventDetail />} />

          {/* Responsável — Portal */}
          <Route path="/responsavel/meus-filhos" element={<MyChildren />} />
          <Route path="/responsavel/meus-filhos/:childId" element={<ChildDetails />} />
          <Route path="/responsavel/meus-filhos/:childId/boletim/:enrollmentId" element={<ReportCard />} />

          {/* Professor — Minhas Turmas */}
          <Route path="/professor/minhas-turmas" element={<MyClasses />} />
          <Route path="/professor/chamadas" element={<Navigate to="/professor/minhas-turmas" replace />} />
          <Route path="/professor/frequencias" element={<Navigate to="/professor/minhas-turmas" replace />} />
          <Route path="/professor/avaliacoes" element={<Navigate to="/professor/minhas-turmas" replace />} />
          <Route path="/professor/turma/:alocacaoId/chamadas" element={<CallsList />} />
          <Route path="/professor/turma/:alocacaoId/chamada/nova" element={<CallForm />} />
          <Route path="/professor/chamada/:callId" element={<FrequencyRegister />} />
          <Route path="/professor/turma/:alocacaoId/avaliacoes" element={<AssessmentsList />} />
          <Route path="/professor/turma/:alocacaoId/avaliacao/nova" element={<AssessmentForm />} />
          <Route path="/professor/avaliacao/:assessmentId/notas" element={<AssessmentGrades />} />
          {/* Professor — Boletins */}
          <Route path="/professor/boletins" element={<ProfessorReportCards />} />
          <Route path="/professor/boletins/:enrollmentId" element={<ReportCard />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
