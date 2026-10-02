import {
  LayoutDashboard,
  Calendar,
  CalendarDays,
  GraduationCap,
  BookOpen,
  Users,
  UserRound,
  School,
  FilePlus,
  ContactRound,
  ClipboardList,
  CheckSquare,
  FileText,
  Award,
  Settings,
  UtensilsCrossed,
  Package,
  BarChart3,
  Kanban,
  ShoppingCart,
  Megaphone,
  Bell,
  AlertTriangle,
  Wallet,
  Sparkles,
  CalendarClock,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  path?: string;
  icon: LucideIcon;
  children?: NavItem[];
}

const adminNav: NavItem[] = [
  { label: "Dashboard", path: "/admin/dashboard", icon: LayoutDashboard },
  { label: "Agenda", path: "/admin/agenda", icon: CalendarDays },
  {
    label: "Cadastros",
    icon: GraduationCap,
    children: [
      { label: "Anos Letivos", path: "/admin/anos-letivos", icon: Calendar },
      { label: "Séries", path: "/admin/series", icon: GraduationCap },
      { label: "Disciplinas", path: "/admin/disciplinas", icon: BookOpen },
      { label: "Professores", path: "/admin/professores", icon: Users },
    ],
  },
  { label: "Alunos", path: "/admin/alunos", icon: UserRound },
  { label: "Turmas", path: "/admin/turmas", icon: School },
  { label: "Matrículas", path: "/admin/matriculas", icon: FilePlus },
  { label: "Alocações", path: "/admin/alocacoes", icon: ContactRound },
  { label: "Grade Horária", path: "/admin/grade-horaria", icon: CalendarClock },
  { label: "Config. Acadêmicas", path: "/admin/configuracoes-academicas", icon: Settings },
  {
    label: "Diário",
    icon: ClipboardList,
    children: [
      { label: "Frequência", path: "/admin/frequencia", icon: CheckSquare },
      { label: "Avaliações", path: "/admin/avaliacoes", icon: FileText },
    ],
  },
  { label: "Boletins", path: "/admin/boletins", icon: Award },
  {
    label: "Comunicação",
    icon: Megaphone,
    children: [
      { label: "Avisos", path: "/admin/avisos", icon: Megaphone },
      { label: "Ocorrências", path: "/admin/ocorrencias", icon: AlertTriangle },
      { label: "Notificações", path: "/admin/notificacoes", icon: Bell },
    ],
  },
  {
    label: "Cantina",
    icon: UtensilsCrossed,
    children: [
      { label: "Gestão", path: "/admin/cantina/gestao", icon: BarChart3 },
      { label: "Atendimento", path: "/admin/cantina/atendimento", icon: ShoppingCart },
      { label: "Cadastro", path: "/admin/cantina/cadastro", icon: Package },
      { label: "Kanban", path: "/admin/cantina/kanban", icon: Kanban },
      { label: "Config.", path: "/admin/cantina-config", icon: Settings },
    ],
  },
  {
    label: "Financeiro",
    icon: Wallet,
    children: [
      { label: "Carteiras", path: "/admin/carteiras", icon: Wallet },
    ],
  },
  { label: "Atena", path: "/admin/atena", icon: Sparkles },
];

const secretariaNav: NavItem[] = [
  { label: "Dashboard", path: "/secretaria/dashboard", icon: LayoutDashboard },
  { label: "Agenda", path: "/secretaria/agenda", icon: CalendarDays },
  { label: "Alunos", path: "/secretaria/alunos", icon: UserRound },
  { label: "Turmas", path: "/secretaria/turmas", icon: School },
  { label: "Matrículas", path: "/secretaria/matriculas", icon: FilePlus },
  { label: "Alocações", path: "/secretaria/alocacoes", icon: ContactRound },
  { label: "Grade Horária", path: "/secretaria/grade-horaria", icon: CalendarClock },
  {
    label: "Cadastros",
    icon: GraduationCap,
    children: [
      { label: "Anos Letivos", path: "/secretaria/anos-letivos", icon: Calendar },
      { label: "Séries", path: "/secretaria/series", icon: GraduationCap },
      { label: "Disciplinas", path: "/secretaria/disciplinas", icon: BookOpen },
      { label: "Professores", path: "/secretaria/professores", icon: Users },
    ],
  },
  {
    label: "Consultas",
    icon: ClipboardList,
    children: [
      { label: "Boletins", path: "/secretaria/boletins", icon: Award },
    ],
  },
  {
    label: "Comunicação",
    icon: Megaphone,
    children: [
      { label: "Avisos", path: "/secretaria/avisos", icon: Megaphone },
      { label: "Ocorrências", path: "/secretaria/ocorrencias", icon: AlertTriangle },
      { label: "Notificações", path: "/secretaria/notificacoes", icon: Bell },
    ],
  },
  { label: "Atena", path: "/secretaria/atena", icon: Sparkles },
];

const professorNav: NavItem[] = [
  { label: "Dashboard", path: "/professor/dashboard", icon: LayoutDashboard },
  { label: "Agenda", path: "/professor/agenda", icon: CalendarDays },
  { label: "Minhas Turmas", path: "/professor/minhas-turmas", icon: School },
  { label: "Ocorrências", path: "/professor/ocorrencias", icon: AlertTriangle },
  { label: "Notificações", path: "/professor/notificacoes", icon: Bell },
  { label: "Atena", path: "/professor/atena", icon: Sparkles },
];

const responsavelNav: NavItem[] = [
  { label: "Dashboard", path: "/responsavel/dashboard", icon: LayoutDashboard },
  { label: "Agenda", path: "/responsavel/agenda", icon: CalendarDays },
  { label: "Meus Filhos", path: "/responsavel/meus-filhos", icon: Users },
  { label: "Avisos", path: "/responsavel/avisos", icon: Megaphone },
  { label: "Ocorrências", path: "/responsavel/ocorrencias", icon: AlertTriangle },
  { label: "Notificações", path: "/responsavel/notificacoes", icon: Bell },
  { label: "Atena", path: "/responsavel/atena", icon: Sparkles },
];

const cantineiroNav: NavItem[] = [
  {
    label: "Cantina",
    icon: UtensilsCrossed,
    children: [
      { label: "Gestão", path: "/cantineiro/cantina/gestao", icon: BarChart3 },
      { label: "Atendimento", path: "/cantineiro/cantina/atendimento", icon: ShoppingCart },
      { label: "Cadastro", path: "/cantineiro/cantina/cadastro", icon: Package },
      { label: "Kanban", path: "/cantineiro/cantina/kanban", icon: Kanban },
    ],
  },
  { label: "Notificações", path: "/cantineiro/notificacoes", icon: Bell },
  { label: "Atena", path: "/cantineiro/atena", icon: Sparkles },
];

const coordenadorNav: NavItem[] = [
  { label: "Avisos", path: "/coordenador/avisos", icon: Megaphone },
  { label: "Ocorrências", path: "/coordenador/ocorrencias", icon: AlertTriangle },
  { label: "Notificações", path: "/coordenador/notificacoes", icon: Bell },
  { label: "Atena", path: "/coordenador/atena", icon: Sparkles },
];

export const navMap: Record<string, NavItem[]> = {
  admin: adminNav,
  secretaria: secretariaNav,
  professor: professorNav,
  responsavel: responsavelNav,
  cantineiro: cantineiroNav,
  coordenador: coordenadorNav,
};
