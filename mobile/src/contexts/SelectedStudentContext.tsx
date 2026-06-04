import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { Child } from "../types/responsavel";

interface SelectedStudentContextType {
  selectedChild: Child | null;
  selectChild: (child: Child) => void;
  clearSelection: () => void;
}

const SelectedStudentContext = createContext<SelectedStudentContextType | null>(null);

export function SelectedStudentProvider({ children }: { children: ReactNode }) {
  const [selectedChild, setSelectedChild] = useState<Child | null>(null);

  const selectChild = useCallback((child: Child) => {
    setSelectedChild(child);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedChild(null);
  }, []);

  return (
    <SelectedStudentContext.Provider
      value={{ selectedChild, selectChild, clearSelection }}
    >
      {children}
    </SelectedStudentContext.Provider>
  );
}

export function useSelectedStudent() {
  const context = useContext(SelectedStudentContext);
  if (!context) {
    throw new Error(
      "useSelectedStudent must be used within SelectedStudentProvider"
    );
  }
  return context;
}
