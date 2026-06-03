import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { addMonths, subMonths, startOfMonth, endOfMonth, format, isSameDay } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { agendaApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Spinner } from "../../components/ui/Spinner";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { EventCard } from "./EventCard";
import { CalendarGrid } from "./CalendarGrid";
import { DayEventsModal } from "./DayEventsModal";

const CAN_CREATE = ["admin", "secretaria", "professor"];

export function AgendaPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;
  const canCreate = user?.perfil && CAN_CREATE.includes(user.perfil);

  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["agenda", format(monthStart, "yyyy-MM"), format(monthEnd, "yyyy-MM")],
    queryFn: () =>
      agendaApi.list({
        page: 1,
        size: 100,
        data_inicio: monthStart.toISOString(),
        data_fim: monthEnd.toISOString(),
      }),
  });

  const eventos = data?.items ?? [];

  const upcomingEventos = useMemo(() => {
    const now = new Date();
    return [...eventos]
      .filter((ev) => new Date(ev.data_inicio) >= now)
      .sort((a, b) => new Date(a.data_inicio).getTime() - new Date(b.data_inicio).getTime())
      .slice(0, 5);
  }, [eventos]);

  const dayEventos = useMemo(() => {
    if (!selectedDay) return [];
    return eventos.filter((ev) => isSameDay(new Date(ev.data_inicio), selectedDay));
  }, [eventos, selectedDay]);

  const handleDayClick = (day: Date) => {
    setSelectedDay(day);
    setModalOpen(true);
  };

  return (
    <div>
      <Breadcrumb items={[{ label: "Agenda" }]} />
      <PageHeader
        title="Agenda"
        description="Gerencie eventos e compromissos"
        showNew={canCreate}
        newLabel="Novo Evento"
        onNew={() => navigate(`${prefix}/agenda/eventos/novo`)}
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Spinner />
        </div>
      ) : isError ? (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">Erro ao carregar eventos.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {upcomingEventos.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                Próximos eventos
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
                {upcomingEventos.map((ev) => (
                  <EventCard
                    key={ev.id}
                    evento={ev}
                    onClick={() => navigate(`${prefix}/agenda/eventos/${ev.id}`)}
                  />
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-3">
              <button
                onClick={() => setCurrentDate((d) => subMonths(d, 1))}
                className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {format(currentDate, "MMMM 'de' yyyy", { locale: ptBR })}
              </h2>
              <button
                onClick={() => setCurrentDate((d) => addMonths(d, 1))}
                className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
            <CalendarGrid
              currentDate={currentDate}
              eventos={eventos}
              onDayClick={handleDayClick}
            />
          </div>
        </div>
      )}

      <DayEventsModal
        open={modalOpen}
        date={selectedDay}
        eventos={dayEventos}
        onClose={() => setModalOpen(false)}
        prefix={prefix}
      />
    </div>
  );
}
