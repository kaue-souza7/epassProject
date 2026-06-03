import { useNavigate } from "react-router-dom";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { MapPin, Clock } from "lucide-react";
import { Modal } from "../../components/ui/Modal";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import type { EventoResponse } from "../../api/endpoints";

interface DayEventsModalProps {
  open: boolean;
  date: Date | null;
  eventos: EventoResponse[];
  onClose: () => void;
  prefix: string;
}

export function DayEventsModal({ open, date, eventos, onClose, prefix }: DayEventsModalProps) {
  const navigate = useNavigate();

  if (!date) return null;

  return (
    <Modal open={open} title={format(date, "dd 'de' MMMM 'de' yyyy", { locale: ptBR })} onClose={onClose}>
      {eventos.length === 0 ? (
        <EmptyState title="Nenhum evento" description="Não há eventos neste dia." />
      ) : (
        <div className="space-y-3">
          {eventos.map((ev) => (
            <div
              key={ev.id}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
            >
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{ev.titulo}</p>
              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {format(new Date(ev.data_inicio), "HH:mm")}h
                  {ev.data_fim && <> — {format(new Date(ev.data_fim), "HH:mm")}h</>}
                </span>
                {ev.local && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {ev.local}
                  </span>
                )}
              </div>
              {ev.descricao && (
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{ev.descricao}</p>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="mt-2"
                onClick={() => {
                  onClose();
                  navigate(`${prefix}/agenda/eventos/${ev.id}`);
                }}
              >
                Mais detalhes
              </Button>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
