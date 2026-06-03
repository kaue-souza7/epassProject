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
];

const secretariaNav: NavItem[] = [
  { label: "Dashboard", path: "/secretaria/dashboard", icon: LayoutDashboard },
  { label: "Agenda", path: "/secretaria/agenda", icon: CalendarDays },
  { label: "Alunos", path: "/secretaria/alunos", icon: UserRound },
  { label: "Turmas", path: "/secretaria/turmas", icon: School },
  { label: "Matrículas", path: "/secretaria/matriculas", icon: FilePlus },
  { label: "Alocações", path: "/secretaria/alocacoes", icon: ContactRound },
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
];

const professorNav: NavItem[] = [
  { label: "Dashboard", path: "/professor/dashboard", icon: LayoutDashboard },
  { label: "Agenda", path: "/professor/agenda", icon: CalendarDays },
  { label: "Minhas Turmas", path: "/professor/minhas-turmas", icon: School },
  { label: "Boletins", path: "/professor/boletins", icon: Award },
];

const responsavelNav: NavItem[] = [
  { label: "Dashboard", path: "/responsavel/dashboard", icon: LayoutDashboard },
  { label: "Agenda", path: "/responsavel/agenda", icon: CalendarDays },
  { label: "Meus Filhos", path: "/responsavel/meus-filhos", icon: Users },
];

export const navMap: Record<string, NavItem[]> = {
  admin: adminNav,
  secretaria: secretariaNav,
  professor: professorNav,
  responsavel: responsavelNav,
};
