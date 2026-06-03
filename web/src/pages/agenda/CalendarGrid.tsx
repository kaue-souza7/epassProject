import { useMemo } from "react";
import {
  startOfMonth, endOfMonth, startOfWeek, endOfWeek,
  eachDayOfInterval, isSameMonth, isToday, format,
} from "date-fns";
import { clsx } from "clsx";
import type { EventoResponse } from "../../api/endpoints";

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

interface CalendarGridProps {
  currentDate: Date;
  eventos: EventoResponse[];
  onDayClick: (date: Date) => void;
}

export function CalendarGrid({ currentDate, eventos, onDayClick }: CalendarGridProps) {
  const days = useMemo(() => {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const calStart = startOfWeek(monthStart, { weekStartsOn: 0 });
    const calEnd = endOfWeek(monthEnd, { weekStartsOn: 0 });
    return eachDayOfInterval({ start: calStart, end: calEnd });
  }, [currentDate]);

  const eventosPorDia = useMemo(() => {
    const map = new Map<string, EventoResponse[]>();
    for (const ev of eventos) {
      const key = format(new Date(ev.data_inicio), "yyyy-MM-dd");
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(ev);
    }
    return map;
  }, [eventos]);

  return (
    <div className="bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="grid grid-cols-7">
        {DIAS_SEMANA.map((d) => (
          <div key={d} className="py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
            {d}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {days.map((day) => {
          const key = format(day, "yyyy-MM-dd");
          const dayEventos = eventosPorDia.get(key) || [];
          const isCurrentMonth = isSameMonth(day, currentDate);
          const isTodayDate = isToday(day);

          return (
            <button
              key={key}
              onClick={() => onDayClick(day)}
              className={clsx(
                "relative flex flex-col items-center py-2 min-h-[56px] transition-colors border-b border-r border-gray-100 dark:border-gray-700/50",
                isCurrentMonth
                  ? "text-gray-900 dark:text-gray-100 hover:bg-primary-50 dark:hover:bg-primary-900/10"
                  : "text-gray-400 dark:text-gray-600",
              )}
            >
              <span
                className={clsx(
                  "flex items-center justify-center w-7 h-7 text-sm rounded-full",
                  isTodayDate && "bg-primary-500 text-white font-bold",
                )}
              >
                {format(day, "d")}
              </span>
              {dayEventos.length > 0 && (
                <div className="flex items-center gap-0.5 mt-0.5">
                  {dayEventos.slice(0, 3).map((_, i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  ))}
                  {dayEventos.length > 3 && (
                    <span className="text-[10px] text-gray-400 font-medium">+{dayEventos.length - 3}</span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
