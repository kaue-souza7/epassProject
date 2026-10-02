"""
Seed FINAL: 5 pedidos do Binio em todos os estágios do Kanban.
Handle fresh DB: create config + products if needed, then create 5 orders.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import asyncpg

BINIO_ALUNO_ID = "32dfd066-a82c-48e5-bc1c-f4704110a186"
BINIO_WALLET_ID = None  # looked up dynamically
CANTINEIRO_ID = "514fa6c9-43d4-4b43-aa53-4eccf96bc154"


def now_utc():
    return datetime.now(timezone.utc)


def days_ago(n):
    return now_utc().replace(hour=14, minute=0, second=0, microsecond=0) - timedelta(days=n)


async def main():
    import os
    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        BINIO = uuid.UUID(BINIO_ALUNO_ID)
        CANTINEIRO = uuid.UUID(CANTINEIRO_ID)

        # Look up wallet dynamically
        WALLET = await conn.fetchval("SELECT id FROM wallets WHERE aluno_id = $1", BINIO)
        if not WALLET:
            WALLET = uuid.uuid4()
            await conn.execute("INSERT INTO wallets (id, aluno_id, saldo, status, created_at, updated_at) VALUES ($1,$2,50.00,'ATIVA'::statuswallet,$3,$3)", WALLET, BINIO, now_utc())
            print(f"Criada wallet para Binio: {WALLET}")
        else:
            print(f"Wallet existente: {WALLET}")

        # ── 1. CANTINA CONFIG ──
        has_config = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM cantina_config)")
        if not has_config:
            print("Criando cantina_config...")
            await conn.execute("""
                INSERT INTO cantina_config (id, aberta, horario_abertura, horario_fechamento, dias_funcionamento, prazo_pedido_minutos, prazo_cancelamento_minutos, observacoes, updated_at)
                VALUES ($1, TRUE, '07:00', '17:00', '1,2,3,4,5', 999999, 1440, 'Cantina escolar', $2)
            """, uuid.uuid4(), now_utc())
        else:
            print("Cantina config existe. Desativando auto-cancel...")
            await conn.execute("UPDATE cantina_config SET prazo_pedido_minutos = 999999, aberta = TRUE")

        # ── 2. AUTONOMIA ──
        await conn.execute("UPDATE alunos SET autonomia_cantina = TRUE WHERE id = $1", BINIO)

        # ── 3. PRODUTOS ──
        prod_count = await conn.fetchval("SELECT COUNT(*) FROM produtos")
        if prod_count == 0:
            print("Criando 10 produtos...")
            produtos = [
                ("Coxinha de Frango", "Coxinha cremosa de frango", 5.50, "SALGADO", 100, 20, "COX001", 2.50, "un", False),
                ("Pastel de Queijo", "Pastel crocante de queijo", 4.00, "SALGADO", 80, 15, "PAS001", 1.80, "un", False),
                ("Pão de Queijo", "Pão de queijo mineiro", 3.00, "LANCHE_QUENTE", 120, 25, "PQJ001", 1.20, "un", False),
                ("Suco de Laranja", "Suco natural 300ml", 4.50, "LANCHE_NATURAL", 60, 10, "SUC001", 1.80, "un", True),
                ("Brigadeiro", "Brigadeiro artesanal", 2.50, "DOCE", 90, 20, "BRI001", 0.80, "un", False),
                ("Bomba de Chocolate", "Bomba recheada de chocolate", 3.50, "DOCE", 70, 15, "BOM001", 1.40, "un", False),
                ("Croissant de Presunto", "Croissant recheado", 6.00, "LANCHE_QUENTE", 50, 10, "CRO001", 2.80, "un", True),
                ("Água Mineral", "Água 500ml", 2.00, "LANCHE_NATURAL", 150, 30, "AGU001", 0.60, "un", False),
                ("Bisnaguinha", "Pão doce mini", 1.50, "BOMBONIERE", 200, 40, "BIS001", 0.50, "un", False),
                ("Sonho de Creme", "Sonho recheado", 4.50, "LANCHE_QUENTE", 40, 10, "SON001", 2.00, "un", True),
            ]
            for p in produtos:
                pid = uuid.uuid4()
                nome, desc, preco, cat, est, est_min, cod, custo, uni, perc = p
                val = (now_utc() + timedelta(days=7)) if perc else None
                await conn.execute("""
                    INSERT INTO produtos (id, nome, descricao, preco, imagem_url, categoria, estoque_atual, estoque_minimo, codigo, custo, unidade_medida, perecivel, data_validade, ativo, created_at, updated_at)
                    VALUES ($1,$2,$3,$4,NULL,$5::categoriaproduto,$6,$7,$8,$9,$10,$11,$12,TRUE,$13,$13)
                """, pid, nome, desc, preco, cat, est, est_min, cod, custo, uni, perc, val, now_utc())
        else:
            print(f"Produtos já existem: {prod_count}")

        # ── 4. CLEAN EXISTING BINIO DATA ──
        pedidos_existentes = await conn.fetchval("SELECT COUNT(*) FROM pedidos WHERE aluno_id = $1", BINIO)
        if pedidos_existentes > 0:
            print(f"Limpando {pedidos_existentes} pedido(s) antigo(s)...")
            await conn.execute("DELETE FROM itens_pedido WHERE pedido_id IN (SELECT id FROM pedidos WHERE aluno_id = $1)", BINIO)
            await conn.execute("DELETE FROM pedidos WHERE aluno_id = $1", BINIO)
            await conn.execute("DELETE FROM movimentacoes_estoque WHERE motivo LIKE '%Binio%'")
            await conn.execute("DELETE FROM movimentacoes WHERE wallet_id = $1 AND tipo = 'CONSUMO'::tipomovimentacao", WALLET)

        # ── 5. RESET WALLET ──
        await conn.execute("UPDATE wallets SET saldo = 50.00 WHERE id = $1", WALLET)

        # ── 6. RESET STOCK ──
        stock = {"COX001": 100, "PAS001": 80, "PQJ001": 120, "SUC001": 60,
                 "BRI001": 90, "BOM001": 70, "CRO001": 50, "AGU001": 150,
                 "BIS001": 200, "SON001": 40}
        for cod, val in stock.items():
            await conn.execute("UPDATE produtos SET estoque_atual = $1 WHERE codigo = $2", val, cod)

        # ── 7. PRODUCT MAP ──
        rows = await conn.fetch("SELECT id, codigo, preco FROM produtos ORDER BY codigo")
        prod_map = {r["codigo"]: {"id": r["id"], "preco": float(r["preco"])} for r in rows}
        print(f"Produtos mapeados ({len(prod_map)}): {list(prod_map.keys())}")

        # ── 8. CREATE 5 ORDERS ──
        pedidos = [
            {"status": "PENDENTE",    "obs": "Coxinha de frango x2",
             "items": [("COX001", 2)], "dias": 4, "debito": 0.00},
            {"status": "APROVADO",    "obs": "Pastel + Pão de Queijo",
             "items": [("PAS001", 1), ("PQJ001", 1)], "dias": 3, "debito": 7.00},
            {"status": "EM_PRODUCAO", "obs": "Sucos + Croissant",
             "items": [("SUC001", 2), ("CRO001", 1)], "dias": 2, "debito": 15.00},
            {"status": "PRONTO",      "obs": "Doces variados",
             "items": [("BRI001", 3), ("BOM001", 1)], "dias": 1, "debito": 11.00},
            {"status": "RETIRADO",    "obs": "Lanche completo",
             "items": [("AGU001", 1), ("BIS001", 1), ("SON001", 1)], "dias": 0, "debito": 8.00},
        ]

        saldos = [50.00, 43.00, 28.00, 17.00, 9.00, 1.00]

        for i, ped in enumerate(pedidos):
            pedido_id = uuid.uuid4()
            created = days_ago(ped["dias"])
            valor_total = sum(prod_map[c]["preco"] * q for c, q in ped["items"])

            mov_id = None
            if ped["status"] != "PENDENTE":
                mov_id = uuid.uuid4()
                await conn.execute("""
                    INSERT INTO movimentacoes (id, wallet_id, tipo, valor, saldo_anterior, saldo_posterior, descricao, criado_por, created_at)
                    VALUES ($1, $2, 'CONSUMO'::tipomovimentacao, $3, $4, $5, $6, $7, $8)
                """, mov_id, WALLET, ped["debito"], saldos[i], saldos[i+1],
                    f"Débito pedido - {ped['obs']}", CANTINEIRO, created)

            print(f"  {ped['status']:15} | R$ {valor_total:.2f} | dia -{ped['dias']} | {ped['obs']}")
            await conn.execute("""
                INSERT INTO pedidos (id, aluno_id, responsavel_id, status, valor_total, saldo_debitado, movimentacao_id, observacoes, created_at, updated_at)
                VALUES ($1,$2,$3,$4::statuspedido,$5,$6,$7,$8,$9,$9)
            """, pedido_id, BINIO, CANTINEIRO, ped["status"], valor_total, ped["debito"], mov_id, ped["obs"], created)

            for codigo, qtd in ped["items"]:
                await conn.execute("""
                    INSERT INTO itens_pedido (id, pedido_id, produto_id, quantidade, preco_unitario, preco_total)
                    VALUES ($1,$2,$3,$4,$5,$6)
                """, uuid.uuid4(), pedido_id, prod_map[codigo]["id"], qtd, prod_map[codigo]["preco"], prod_map[codigo]["preco"] * qtd)
                estoque_antes = await conn.fetchval("SELECT estoque_atual FROM produtos WHERE codigo = $1", codigo)
                await conn.execute("""
                    INSERT INTO movimentacoes_estoque (id, produto_id, tipo, quantidade, estoque_anterior, estoque_atual, motivo, usuario_id, created_at)
                    VALUES ($1,$2,'SAIDA'::tipomovimentacaoestoque,$3,$4,$5,$6,$7,$8)
                """, uuid.uuid4(), prod_map[codigo]["id"], qtd, estoque_antes, estoque_antes - qtd, f"Pedido Binio - {ped['obs']}", CANTINEIRO, created)
                await conn.execute("UPDATE produtos SET estoque_atual = estoque_atual - $1 WHERE codigo = $2", qtd, codigo)

        total_debitado = sum(p["debito"] for p in pedidos if p["debito"] > 0)
        await conn.execute("UPDATE wallets SET saldo = $1 WHERE id = $2", 50.00 - total_debitado, WALLET)

        # ── 9. VERIFY ──
        print("\n=== RESULTADO FINAL ===")
        rows = await conn.fetch("""
            SELECT p.status, p.valor_total, p.observacoes, p.created_at::date
            FROM pedidos p WHERE p.aluno_id = $1 ORDER BY p.created_at
        """, BINIO)
        for r in rows:
            print(f"  {r['status']:15} | R$ {r['valor_total']:.2f} | {r['observacoes']} | {r['created_at']}")

        saldo = await conn.fetchval("SELECT saldo FROM wallets WHERE id = $1", WALLET)
        print(f"\nSaldo final: R$ {saldo:.2f}")
        print(f"Pedidos: {len(rows)}")
        print("SEED CONCLUIDO COM SUCESSO")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
