import { Calendar, MapPin } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import type { EventoResponse } from "../../api/endpoints";

interface EventCardProps {
  evento: EventoResponse;
  onClick?: () => void;
}

export function EventCard({ evento, onClick }: EventCardProps) {
  const hora = format(new Date(evento.data_inicio), "HH:mm", { locale: ptBR });

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-4 p-4 bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-primary-300 dark:hover:border-primary-600 transition-all text-left w-full min-w-0"
    >
      <div className="flex-shrink-0 w-14 h-14 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex flex-col items-center justify-center text-primary-600 dark:text-primary-400">
        <span className="text-xs font-medium uppercase">{format(new Date(evento.data_inicio), "MMM", { locale: ptBR })}</span>
        <span className="text-lg font-bold leading-tight">{format(new Date(evento.data_inicio), "dd", { locale: ptBR })}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">{evento.titulo}</p>
        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {hora}h
          </span>
          {evento.local && (
            <span className="flex items-center gap-1 truncate">
              <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="truncate">{evento.local}</span>
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
