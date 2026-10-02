import {
  isValidElement,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from "react";
import { ChevronDown } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import "./BranchedMenu.css";

/** Padding vertical da árvore de filhos; base do cálculo das ramificações. */
const TREE_PAD = 6;
/** Altura do marcador que desliza pelo trilho. */
const MARK = 16;

export type BranchedMenuTone = "default" | "danger";

export interface BranchedMenuItem {
  /**
   * Identificador estável do item. No menu de navegação do ePass é a própria
   * rota, o que faz dele a chave de estado ativo, de foco e de navegação.
   */
  value: string;
  label: string;
  /** Componente Lucide ou qualquer ReactNode já pronto. */
  icon?: LucideIcon | ReactNode;
  /** Linha secundária. */
  hint?: string;
  /** Conteúdo à direita (badge, chevron, switch). */
  trailing?: ReactNode;
  /** Tom visual — `danger` para ações destrutivas. */
  tone?: BranchedMenuTone;
  disabled?: boolean;
  /**
   * Item com filhos vira seção recolhível; item sem filhos é uma folha que
   * seleciona. É a mesma regra do Branched Menu original.
   */
  children?: BranchedMenuItem[];
  /**
   * URL equivalente. Quando presente o item é renderizado como `<a>`, o que
   * preserva "abrir em nova aba", copiar link e a semântica de navegação.
   * Cliques simples são interceptados e reportados em `onSelect`.
   */
  href?: string;
}

export interface BranchedMenuItemState {
  active: boolean;
  open: boolean;
  focused: boolean;
  disabled: boolean;
}

export interface BranchedMenuProps {
  items: BranchedMenuItem[];
  /** Valor ativo controlado (ex.: `location.pathname`). */
  activeValue?: string;
  defaultActive?: string;
  onActiveChange?: (value: string, item: BranchedMenuItem) => void;
  /** Dispara ao escolher uma folha ou uma seção sem filhos. */
  onSelect?: (value: string, item: BranchedMenuItem) => void;
  /** Seções abertas (controlado, por `value`). */
  openValues?: string[];
  /** Seções abertas iniciais, por índice. `[]` ou `-1` abre nenhuma. */
  defaultOpen?: number | number[];
  onOpenChange?: (values: string[]) => void;
  onToggle?: (value: string, open: boolean) => void;
  /** Abre a seção que contém o item ativo. Padrão: `true`. */
  openActiveSection?: boolean;

  /** Cores — omitir para herdar o tema do projeto. */
  color?: string;
  accentColor?: string;
  lineColor?: string;

  /** Geometria. As alturas reais das linhas são medidas em runtime. */
  width?: number;
  rowHeight?: number;
  indent?: number;
  trunk?: number;
  radius?: number;
  lineWidth?: number;
  fontSize?: number;
  drawDuration?: number;
  foldDuration?: number;

  /** Rótulo acessível da árvore. */
  label?: string;
  className?: string;
  /**
   * Desenha as folhas de nível raiz como ramificações de um tronco implícito.
   * Menus planos (ações da conta, resultados de busca, lista de
   * notificações) ganham a mesma linguagem visual sem precisar de um cabeçalho
   * de seção que não existe. Padrão: `false`.
   */
  branchLeaves?: boolean;
  /** Substitui o desenho padrão da linha (menus com conteúdo rico). */
  renderItem?: (item: BranchedMenuItem, state: BranchedMenuItemState) => ReactNode;
}

interface RowBox {
  top: number;
  height: number;
}

interface BranchPath {
  value: string;
  active: boolean;
  /** Curva horizontal que liga o tronco ao rótulo. */
  base: string;
  /** Mesma curva, porém subindo do topo do tronco — é a linha de acento. */
  reach: string;
  /** Comprimento do traço, usado no `stroke-dasharray`. */
  length: number;
  /** Onde o tronco vertical deve terminar. */
  trunkEnd: number;
}

/** Ramificações de uma seção, na ordem em que os filhos aparecem. */
type SectionBranches = BranchPath[];

function toIndexes(open: number | number[] | undefined): number[] {
  if (open === undefined) return [];
  return Array.isArray(open) ? open : open >= 0 ? [open] : [];
}

function isComponentLike(icon: unknown): icon is LucideIcon {
  return typeof icon === "function" || (typeof icon === "object" && icon !== null);
}

function sameGeometry(a: Record<string, RowBox>, b: Record<string, RowBox>): boolean {
  const keys = Object.keys(b);
  if (Object.keys(a).length !== keys.length) return false;
  return keys.every((key) => {
    const prev = a[key];
    const next = b[key];
    return (
      !!prev &&
      !!next &&
      Math.abs(prev.top - next.top) < 0.5 &&
      Math.abs(prev.height - next.height) < 0.5
    );
  });
}

export function BranchedMenu({
  items,
  activeValue,
  defaultActive = "",
  onActiveChange,
  onSelect,
  openValues,
  defaultOpen,
  onOpenChange,
  onToggle,
  openActiveSection = true,
  color,
  accentColor,
  lineColor,
  width = 240,
  rowHeight = 36,
  indent = 40,
  trunk = 14,
  radius = 10,
  lineWidth = 1.5,
  fontSize = 14,
  drawDuration = 400,
  foldDuration = 300,
  label = "Menu",
  className,
  branchLeaves = false,
  renderItem,
}: BranchedMenuProps) {
  const [innerActive, setInnerActive] = useState(defaultActive);
  const active = activeValue !== undefined ? activeValue : innerActive;

  const [innerOpen, setInnerOpen] = useState<number[]>(() => toIndexes(defaultOpen));
  const openIndexes = useMemo(
    () =>
      openValues !== undefined
        ? openValues
            .map((value) => items.findIndex((i) => i.value === value))
            .filter((i) => i >= 0)
        : innerOpen,
    [openValues, innerOpen, items],
  );
  const openKey = openIndexes.join("|");
  const openSet = useMemo(() => new Set<number>(openIndexes), [openKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const itemByValue = useMemo(() => {
    const map = new Map<string, BranchedMenuItem>();
    items.forEach((item) => {
      map.set(item.value, item);
      item.children?.forEach((child) => map.set(child.value, child));
    });
    return map;
  }, [items]);

  // Tronco implícito para as folhas de nível raiz, quando `branchLeaves` está
  // ligado. Elas são desenhadas em grupo, na posição da primeira folha da lista.
  const rootLeaves = useMemo(
    () => (branchLeaves ? items.filter((item) => !item.children?.length) : []),
    [branchLeaves, items],
  );
  const rootLeafIndex = rootLeaves.length > 0 ? items.indexOf(rootLeaves[0]) : -1;

  /* -------------------------------------------------------------- estado --- */

  const commitOpen = useCallback(
    (next: number[]) => {
      if (openValues === undefined) setInnerOpen(next);
      onOpenChange?.(
        next
          .map((i) => items[i]?.value)
          .filter((value): value is string => Boolean(value)),
      );
    },
    [openValues, onOpenChange, items],
  );

  const toggle = useCallback(
    (index: number) => {
      const item = items[index];
      if (!item?.children) return;
      const isOpen = !openSet.has(index);
      const next = new Set(openIndexes);
      if (isOpen) next.add(index);
      else next.delete(index);
      commitOpen([...next]);
      onToggle?.(item.value, isOpen);
    },
    [items, openSet, openIndexes, commitOpen, onToggle],
  );

  const select = useCallback(
    (value: string, item: BranchedMenuItem) => {
      if (item.disabled) return;
      if (activeValue === undefined) setInnerActive(value);
      onActiveChange?.(value, item);
      onSelect?.(value, item);
    },
    [activeValue, onActiveChange, onSelect],
  );

  // Abre a seção dona do item ativo — evita um menu "fechado" sobre a rota atual.
  useEffect(() => {
    if (!openActiveSection || !active) return;
    const index = items.findIndex((i) => i.children?.some((c) => c.value === active));
    if (index < 0 || openSet.has(index)) return;
    commitOpen([...openIndexes, index]);
  }, [active, openActiveSection, items, openSet, openIndexes, commitOpen]);

  /* ----------------------------------------------------------- geometria --- */

  const nodeRefs = useRef(new Map<string, HTMLElement>());
  const rowRefs = useRef(new Map<string, HTMLElement>());
  const markerRef = useRef<HTMLSpanElement | null>(null);
  const [geometry, setGeometry] = useState<Record<string, RowBox>>({});
  const geometryRef = useRef<Record<string, RowBox>>(geometry);
  geometryRef.current = geometry;

  const measure = useCallback(() => {
    const next: Record<string, RowBox> = {};
    rowRefs.current.forEach((el, value) => {
      const tree = el.parentElement;
      if (!tree) return;
      const base = tree.getBoundingClientRect();
      const box = el.getBoundingClientRect();
      next[value] = { top: box.top - base.top, height: box.height };
    });
    if (!sameGeometry(geometryRef.current, next)) {
      geometryRef.current = next;
      setGeometry(next);
    }
  }, []);

  // Roda após cada render: mantém o trilho alinhado a linhas de altura
  // variável (rótulos que quebram, conteúdo rico, fonte carregando).
  useLayoutEffect(measure);

  useEffect(() => {
    const trees = new Set<HTMLElement>();
    rowRefs.current.forEach((el) => {
      if (el.parentElement) trees.add(el.parentElement);
    });
    if (trees.size === 0) return;
    const observer = new ResizeObserver(() => measure());
    trees.forEach((tree) => observer.observe(tree));
    return () => observer.disconnect();
  }, [openKey, items, measure]);

  useEffect(() => {
    const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
    fonts?.ready.then(() => measure()).catch(() => undefined);
  }, [measure]);

  /* ---------------------------------------------------------------- foco --- */

  const [focusValue, setFocusValue] = useState<string | null>(
    () => defaultActive || items[0]?.value || null,
  );

  const visible = useMemo(() => {
    const out: { value: string; parent: string | null }[] = [];
    items.forEach((item, i) => {
      if (!item.children?.length && rootLeafIndex >= 0) {
        // As folhas de raiz são desenhadas em grupo, na posição da primeira.
        if (i === rootLeafIndex) {
          rootLeaves.forEach((leaf) => out.push({ value: leaf.value, parent: null }));
        }
        return;
      }
      out.push({ value: item.value, parent: null });
      if (item.children && openSet.has(i)) {
        item.children.forEach((child) => out.push({ value: child.value, parent: item.value }));
      }
    });
    return out;
  }, [items, openSet, rootLeafIndex, rootLeaves]);

  // Garante que exista exatamente um ponto focalizável na árvore — inclusive
  // depois de uma seção fechar em cima do item que estava em foco.
  useEffect(() => {
    const reachable = visible.some((v) => v.value === focusValue);
    if (reachable) return;
    const activeReachable = visible.some((v) => v.value === active);
    setFocusValue(activeReachable ? active : (visible[0]?.value ?? null));
  }, [focusValue, visible, active]);

  const focusNode = useCallback((value: string) => {
    setFocusValue(value);
    nodeRefs.current.get(value)?.focus();
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      const value = (event.target as HTMLElement).getAttribute("data-value");
      if (!value) return;

      const index = visible.findIndex((v) => v.value === value);
      const node = itemByValue.get(value);
      if (index < 0 || !node) return;

      const move = (delta: number) => {
        const next = visible[Math.min(Math.max(index + delta, 0), visible.length - 1)];
        if (next) focusNode(next.value);
      };

      switch (event.key) {
        case "ArrowDown":
          move(1);
          break;
        case "ArrowUp":
          move(-1);
          break;
        case "Home":
          if (visible[0]) focusNode(visible[0].value);
          break;
        case "End":
          if (visible.length) focusNode(visible[visible.length - 1].value);
          break;
        case "ArrowRight": {
          const sectionIndex = items.findIndex((i) => i.value === value);
          if (!node.children || sectionIndex < 0) return;
          if (!openSet.has(sectionIndex)) toggle(sectionIndex);
          else if (node.children[0]) focusNode(node.children[0].value);
          break;
        }
        case "ArrowLeft": {
          const parent = visible[index].parent;
          if (parent) {
            focusNode(parent);
            break;
          }
          const sectionIndex = items.findIndex((i) => i.value === value);
          if (sectionIndex < 0 || !openSet.has(sectionIndex)) return;
          toggle(sectionIndex);
          break;
        }
        default:
          return;
      }
      event.preventDefault();
    },
    [visible, itemByValue, items, openSet, toggle, focusNode],
  );

  /* ----------------------------------------------------------------- SVG --- */

  // Linha de topo ativa: a folha selecionada ou a seção dona do item ativo.
  const activeTopIndex = items.findIndex(
    (i) =>
      (!i.children && i.value === active) || (i.children?.some((c) => c.value === active) ?? false),
  );
  const markerOn =
    activeTopIndex >= 0 && (items[activeTopIndex].children ? openSet.has(activeTopIndex) : true);

  useLayoutEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    const head =
      activeTopIndex >= 0 ? nodeRefs.current.get(items[activeTopIndex]?.value ?? "") : undefined;
    if (markerOn && head) {
      marker.style.top = `${head.offsetTop + (head.offsetHeight - MARK) / 2}px`;
    }
    marker.toggleAttribute("data-on", Boolean(markerOn && head));
  }, [activeTopIndex, markerOn, openKey, items]);

  const buildBranches = useCallback(
    (children: BranchedMenuItem[]): SectionBranches => {
      const endX = indent - 8;
      return children.map((child, k) => {
        const box = geometry[child.value];
        const height = box?.height ?? rowHeight;
        const top = box?.top ?? TREE_PAD + k * rowHeight;
        const r = Math.max(0, Math.min(radius, height / 2 - 2));
        const y = top + height / 2;
        const tail = `A ${r} ${r} 0 0 0 ${trunk + r} ${y} H ${endX}`;
        return {
          value: child.value,
          active: child.value === active,
          base: `M ${trunk} ${y - r} ${tail}`,
          reach: `M ${trunk} 0 V ${y - r} ${tail}`,
          length: y - r + (Math.PI * r) / 2 + (endX - trunk - r),
          trunkEnd: y - r,
        } satisfies BranchPath;
      });
    },
    [geometry, active, radius, rowHeight, indent, trunk],
  );

  const branchPaths = useMemo<SectionBranches[]>(
    () => items.map((item) => (item.children ? buildBranches(item.children) : [])),
    [items, buildBranches],
  );

  const rootPaths = useMemo(() => buildBranches(rootLeaves), [buildBranches, rootLeaves]);

  /* -------------------------------------------------------------- render --- */

  const rootStyle = {
    "--bm-w": `${width}px`,
    "--bm-ink": color,
    "--bm-accent": accentColor,
    "--bm-line": lineColor,
    // rowHeight/fontSize vão para variáveis "-base" para que as media queries
    // de toque grosso (@media (pointer: coarse)) ainda possam elevá-las.
    // Uma custom property inline sempre venceria uma regra de stylesheet.
    "--bm-font-base": `${fontSize}px`,
    "--bm-row-base": `${rowHeight}px`,
    "--bm-indent": `${indent}px`,
    "--bm-line-w": lineWidth,
    "--bm-draw": `${drawDuration}ms`,
    "--bm-fold": `${foldDuration}ms`,
  } as CSSProperties;

  const renderIcon = (icon: BranchedMenuItem["icon"], variant: "head" | "item") => {
    if (!icon) return null;
    if (isValidElement(icon)) return icon;
    if (isComponentLike(icon)) {
      const Icon = icon;
      return <Icon className={`bm__icon bm__icon--${variant}`} aria-hidden="true" />;
    }
    return null;
  };

  const handleActivate = (event: MouseEvent, item: BranchedMenuItem) => {
    // Cliques modificados preservam o comportamento nativo do link
    // (nova aba, nova janela, copiar endereço do item).
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
      return;
    }
    event.preventDefault();
    select(item.value, item);
  };

  const defaultContent = (item: BranchedMenuItem) => (
    <>
      {renderIcon(item.icon, "item")}
      <span className="bm__text">
        <span className="bm__label">{item.label}</span>
        {item.hint ? <span className="bm__hint">{item.hint}</span> : null}
      </span>
      {item.trailing ? <span className="bm__trailing">{item.trailing}</span> : null}
    </>
  );

  const renderRow = (child: BranchedMenuItem, level: 1 | 2, reachable: boolean) => {
    const state: BranchedMenuItemState = {
      active: child.value === active,
      open: false,
      focused: focusValue === child.value,
      disabled: Boolean(child.disabled),
    };
    const shared = {
      "data-value": child.value,
      "data-active": state.active ? "" : undefined,
      "data-tone": child.tone === "danger" ? "danger" : undefined,
      "aria-disabled": child.disabled || undefined,
      "aria-current": state.active ? ("page" as const) : undefined,
      "aria-level": level,
      tabIndex: state.focused && reachable ? 0 : -1,
      onClick: (event: MouseEvent) => {
        setFocusValue(child.value);
        handleActivate(event, child);
      },
    };
    const register = (el: HTMLElement | null) => {
      if (!el) {
        nodeRefs.current.delete(child.value);
        rowRefs.current.delete(child.value);
        return;
      }
      nodeRefs.current.set(child.value, el);
      rowRefs.current.set(child.value, el);
    };

    return child.href ? (
      <a
        key={child.value}
        ref={register}
        href={child.href}
        role="treeitem"
        className="bm__item"
        {...shared}
      >
        {renderItem ? renderItem(child, state) : defaultContent(child)}
      </a>
    ) : (
      <button
        key={child.value}
        ref={register}
        type="button"
        role="treeitem"
        className="bm__item"
        {...shared}
      >
        {renderItem ? renderItem(child, state) : defaultContent(child)}
      </button>
    );
  };

  const renderTree = (
    paths: SectionBranches,
    children: BranchedMenuItem[],
    isOpen: boolean,
    level: 1 | 2 = 2,
  ) => (
    <div className="bm__tree" role="none">
      <svg
        className="bm__lines"
        width={indent}
        height="100%"
        aria-hidden="true"
        focusable="false"
      >
        {paths.length > 0 ? (
          <>
            <path
              className="bm__base"
              d={`M ${trunk} 0 V ${paths[paths.length - 1].trunkEnd}`}
            />
            {paths.map((path) => (
              <path key={`base-${path.value}`} className="bm__base" d={path.base} />
            ))}
            {paths.map((path) => (
              <path
                key={`reach-${path.value}`}
                className="bm__reach"
                d={path.reach}
                style={{
                  strokeDasharray: path.length,
                  strokeDashoffset: path.active ? 0 : path.length,
                }}
              />
            ))}
          </>
        ) : null}
      </svg>
      {children.map((child) => renderRow(child, level, isOpen))}
    </div>
  );

  return (
    <nav
      className={className ? `bm ${className}` : "bm"}
      style={rootStyle}
      role="tree"
      aria-label={label}
      aria-orientation="vertical"
      onKeyDown={handleKeyDown}
    >
      <span ref={markerRef} className="bm__marker" aria-hidden="true" />

      {items.map((item, i) => {
        const isSection = Boolean(item.children?.length);

        // As folhas de raiz são desenhadas em grupo, na posição da primeira
        // delas. O teste do grupo precisa vir antes do descarte das demais.
        if (i === rootLeafIndex) {
          return (
            <div key={item.value} className="bm__section" data-open="" role="none">
              {renderTree(rootPaths, rootLeaves, true, 1)}
            </div>
          );
        }
        if (!isSection && rootLeafIndex >= 0) return null;

        const isOpen = isSection && openSet.has(i);
        const isActive = !isSection && item.value === active;

        return (
          <div
            key={item.value}
            className="bm__section"
            data-open={isOpen ? "" : undefined}
            role="none"
          >
            <button
              ref={(el) => {
                if (el) nodeRefs.current.set(item.value, el);
                else nodeRefs.current.delete(item.value);
              }}
              type="button"
              role="treeitem"
              className="bm__head"
              data-value={item.value}
              data-active={isActive ? "" : undefined}
              aria-level={1}
              aria-expanded={isSection ? isOpen : undefined}
              aria-current={isActive ? "page" : undefined}
              aria-disabled={item.disabled || undefined}
              tabIndex={focusValue === item.value ? 0 : -1}
              onClick={() => {
                setFocusValue(item.value);
                if (isSection) toggle(i);
                else select(item.value, item);
              }}
            >
              {renderIcon(item.icon, "head")}
              <span className="bm__text">
                <span className="bm__label">{item.label}</span>
                {item.hint ? <span className="bm__hint">{item.hint}</span> : null}
              </span>
              <span className="bm__chev" aria-hidden="true">
                {isSection ? <ChevronDown /> : null}
              </span>
            </button>

            {isSection ? (
              <div className="bm__body" role="group" aria-hidden={!isOpen}>
                <div className="bm__fold">{renderTree(branchPaths[i], item.children!, isOpen)}</div>
              </div>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}
