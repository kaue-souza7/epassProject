import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useLocation } from "react-router-dom";
import { EASE_EPASS } from "./transitions";

/** Tempo que a barra leva para percorrer e desaparecer. */
const DURACAO = 0.7;

export function RouteProgress() {
  const { pathname } = useLocation();
  const reduceMotion = useReducedMotion();
  const [visivel, setVisivel] = useState(false);
  const montagemInicial = useRef(true);
  // Ref evita que trocar a preferência de movimento dispare a barra sozinha.
  const reduzirRef = useRef(reduceMotion);
  reduzirRef.current = reduceMotion;

  useEffect(() => {
    // A barra é reagida à troca de rota. Ela NÃO pode vir de `useNavigation`:
    // esse hook só existe em data routers (`createBrowserRouter`), e o app usa
    // <BrowserRouter> + <Routes>, que não expõe o estado de navegação.
    if (montagemInicial.current) {
      montagemInicial.current = false;
      return;
    }
    if (reduzirRef.current) return;

    setVisivel(true);
    const timer = setTimeout(() => setVisivel(false), DURACAO * 1000);
    return () => clearTimeout(timer);
  }, [pathname]);

  if (reduceMotion) return null;

  return (
    <AnimatePresence>
      {visivel && (
        <motion.div
          key={pathname}
          className="fixed top-0 left-0 right-0 z-[90] h-[3px] pointer-events-none overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.25 } }}
          aria-hidden="true"
        >
          <motion.div
            className="h-full w-full origin-left bg-gradient-to-r from-primary-500 via-accent-400 to-primary-400 shadow-epass-primary"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: DURACAO, ease: EASE_EPASS }}
          />
          <div className="absolute inset-0 overflow-hidden">
            <div className="h-full w-1/3 animate-bar bg-gradient-to-r from-transparent via-white/70 to-transparent" />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
