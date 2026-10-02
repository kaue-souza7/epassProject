"""
Seed script for Cantina module - fictitious data.
Run: docker exec -it epass-backend python seed_cantina.py
"""
import asyncio
import uuid
import random
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://epass:epass123@epass-postgres:5432/epass",
)
engine = create_async_engine(DATABASE_URL)

now = datetime.now(timezone.utc)
today = date.today()

# ── IDs fixos reutilizados ──────────────────────────────────────

RESP_ID = uuid.UUID("2c732a8b-5e33-4dfc-a5d0-7a7712a6fcff")  # Binio (responsavel)
CANT_ID = uuid.UUID("49f550cd-dc8f-4b17-9f3c-dfa31a4c2948")  # Maria Cantina (cantineiro)
ADMIN_ID = uuid.UUID("8efffe3b-b3eb-4d0e-b576-1cabe40ef207")  # Kaue Coordenador

# New students
STUDENTS = [
    {"id": uuid.uuid4(), "nome": "Ana Clara Souza", "turma": "5A", "autonomia": True},
    {"id": uuid.uuid4(), "nome": "Pedro Henrique Lima", "turma": "5B", "autonomia": True},
    {"id": uuid.uuid4(), "nome": "Juliana Ferreira", "turma": "6A", "autonomia": True},
    {"id": uuid.uuid4(), "nome": "Lucas Oliveira", "turma": "6B", "autonomia": False},
    {"id": uuid.uuid4(), "nome": "Mariana Santos", "turma": "7A", "autonomia": True},
    {"id": uuid.uuid4(), "nome": "Gabriel Costa", "turma": "7B", "autonomia": True},
    {"id": uuid.uuid4(), "nome": "Camila Ribeiro", "turma": "8A", "autonomia": True},
    {"id": uuid.uuid4(), "nome": "Rafael Almeida", "turma": "8B", "autonomia": False},
    {"id": uuid.uuid4(), "nome": "Fernanda Rodrigues", "turma": "9A", "autonomia": True},
    {"id": uuid.uuid4(), "nome": "Thiago Martins", "turma": "9B", "autonomia": True},
]

# Existing students
EXISTING_STUDENTS = [
    uuid.UUID("30c81d80-945e-4d63-a633-8e492a431c93"),  # Aluno Binio 1
    uuid.UUID("a7d1f555-62eb-4aa7-8671-c3d760edc3a6"),  # Aluno Binio 2
]

ALL_STUDENT_IDS = [s["id"] for s in STUDENTS] + EXISTING_STUDENTS

# ── Products ────────────────────────────────────────────────────

PRODUCTS = [
    # SALGADOS
    {"nome": "Coxinha de Frango", "descricao": "Coxinha cremosa de frango desfiado", "preco": 4.50, "custo": 2.00, "categoria": "SALGADO", "estoque": 50, "minimo": 10, "codigo": "SAL001", "perecivel": True},
    {"nome": "Pastel de Carne", "descricao": "Pastel frito recheado com carne moída", "preco": 4.00, "custo": 1.80, "categoria": "SALGADO", "estoque": 40, "minimo": 10, "codigo": "SAL002", "perecivel": True},
    {"nome": "Kibe", "descricao": "Kibe assado de carne moída e trigo", "preco": 3.50, "custo": 1.50, "categoria": "SALGADO", "estoque": 35, "minimo": 8, "codigo": "SAL003", "perecivel": True},
    {"nome": "Empada de Queijo", "descricao": "Empada pequena com queijo", "preco": 3.00, "custo": 1.20, "categoria": "SALGADO", "estoque": 30, "minimo": 10, "codigo": "SAL004", "perecivel": True},
    {"nome": "Bolinho de Bacalhau", "descricao": "Bolinho português de bacalhau", "preco": 5.00, "custo": 2.50, "categoria": "SALGADO", "estoque": 0, "minimo": 5, "codigo": "SAL005", "perecivel": True},

    # LANCHE QUENTE
    {"nome": "X-Salada", "descricao": "Hambúrguer com queijo, alface e tomate", "preco": 12.00, "custo": 6.00, "categoria": "LANCHE_QUENTE", "estoque": 25, "minimo": 5, "codigo": "LQ001", "perecivel": True},
    {"nome": "Hot Dog Completo", "descricao": "Cachorro quente com purê, milho e batata palha", "preco": 10.00, "custo": 4.50, "categoria": "LANCHE_QUENTE", "estoque": 20, "minimo": 5, "codigo": "LQ002", "perecivel": True},
    {"nome": "Sanduíche Natural", "descricao": "Pão integral com frango, cenoura e maionese", "preco": 7.00, "custo": 3.00, "categoria": "LANCHE_QUENTE", "estoque": 3, "minimo": 8, "codigo": "LQ003", "perecivel": True},

    # LANCHE NATURAL
    {"nome": "Suco Natural de Laranja", "descricao": "Suco espremido na hora", "preco": 6.00, "custo": 2.50, "categoria": "LANCHE_NATURAL", "estoque": 60, "minimo": 15, "codigo": "LN001", "perecivel": True},
    {"nome": "Vitamina de Banana", "descricao": "Vitamina batida com leite e banana", "preco": 5.50, "custo": 2.00, "categoria": "LANCHE_NATURAL", "estoque": 40, "minimo": 10, "codigo": "LN002", "perecivel": True},
    {"nome": "Água Mineral 500ml", "descricao": "Água mineral sem gás", "preco": 2.50, "custo": 0.80, "categoria": "LANCHE_NATURAL", "estoque": 100, "minimo": 20, "codigo": "LN003", "perecivel": False},

    # DOCES
    {"nome": "Brigadeiro", "descricao": "Brigadeiro tradicional caseiro", "preco": 2.50, "custo": 0.80, "categoria": "DOCE", "estoque": 80, "minimo": 20, "codigo": "DOC001", "perecivel": True},
    {"nome": "Bolo de Chocolate", "descricao": "Fatia de bolo fofinho de chocolate", "preco": 5.00, "custo": 2.00, "categoria": "DOCE", "estoque": 15, "minimo": 5, "codigo": "DOC002", "perecivel": True},
    {"nome": "Pudim de Leite", "descricao": "Fatia de pudim de leite condensado", "preco": 4.50, "custo": 1.80, "categoria": "DOCE", "estoque": 0, "minimo": 5, "codigo": "DOC003", "perecivel": True},

    # BOMBONIERE
    {"nome": "Barra de Cereal", "descricao": "Barra de cereal com mel e frutas", "preco": 3.50, "custo": 1.50, "categoria": "BOMBONIERE", "estoque": 45, "minimo": 10, "codigo": "BOM001", "perecivel": False},
    {"nome": "Pacote de Biscoitos", "descricao": "Pacote com 4 biscoitos de chuva", "preco": 4.00, "custo": 1.60, "categoria": "BOMBONIERE", "estoque": 30, "minimo": 8, "codigo": "BOM002", "perecivel": False},
]


async def seed():
    async with engine.begin() as conn:
        print("=" * 60)
        print("SEED CANTINA - DADOS FICTÍCIOS")
        print("=" * 60)

        # ── 1. Create students ────────────────────────────────
        print("\n[1/8] Criando alunos...")
        for s in STUDENTS:
            await conn.execute(text("""
                INSERT INTO alunos (id, nome, data_nascimento, cpf, data_entrada, ativo, autonomia_cantina, created_at, updated_at)
                VALUES (:id, :nome, :data_nasc, :cpf, :data_entrada, true, :autonomia, :now, :now)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": s["id"], "nome": s["nome"],
                "data_nasc": date(2014, 1, 1), "cpf": f"{random.randint(10000000000, 99999999999)}",
                "data_entrada": date(2023, 2, 1), "autonomia": s["autonomia"], "now": now,
            })
            # Link to resp Binio
            await conn.execute(text("""
                INSERT INTO responsavel_aluno (aluno_id, responsavel_id, parentesco, responsavel_financeiro)
                VALUES (:aluno_id, :resp_id, 'PAI', true)
                ON CONFLICT DO NOTHING
            """), {"aluno_id": s["id"], "resp_id": RESP_ID})
        print(f"   Criados {len(STUDENTS)} alunos + vinculados ao responsável")

        # ── 2. Create wallets + top-up ────────────────────────
        print("\n[2/8] Criando carteiras e recarregando saldos...")
        for s in STUDENTS:
            wallet_id = uuid.uuid4()
            saldo = Decimal(str(random.choice([50.00, 80.00, 100.00, 150.00, 200.00])))
            await conn.execute(text("""
                INSERT INTO wallets (id, aluno_id, saldo, status, created_at, updated_at)
                VALUES (:id, :aluno_id, :saldo, 'ATIVA', :now, :now)
                ON CONFLICT (aluno_id) DO UPDATE SET saldo = wallets.saldo + :saldo
            """), {"id": wallet_id, "aluno_id": s["id"], "saldo": saldo, "now": now})
            # Create recarga movimentacao
            await conn.execute(text("""
                INSERT INTO movimentacoes (id, wallet_id, tipo, valor, saldo_anterior, saldo_posterior, descricao, criado_por, created_at)
                VALUES (:id, :wallet_id, 'RECARGA', :valor, 0, :saldo, 'Recarga inicial via seed', :criado_por, :now)
            """), {
                "id": uuid.uuid4(), "wallet_id": wallet_id, "valor": saldo,
                "saldo": saldo, "criado_por": ADMIN_ID, "now": now,
            })
        print(f"   {len(STUDENTS)} carteiras criadas com saldos entre R$50 e R$200")

        # Also top up existing students
        for sid in EXISTING_STUDENTS:
            saldo = Decimal("120.00")
            await conn.execute(text("""
                INSERT INTO wallets (id, aluno_id, saldo, status, created_at, updated_at)
                VALUES (:id, :aluno_id, :saldo, 'ATIVA', :now, :now)
                ON CONFLICT (aluno_id) DO UPDATE SET saldo = wallets.saldo + :saldo
            """), {"id": uuid.uuid4(), "aluno_id": sid, "saldo": saldo, "now": now})
        print(f"   {len(EXISTING_STUDENTS)} carteiras existentes recarregadas com R$120")

        # ── 3. Create CantinaConfig ───────────────────────────
        print("\n[3/8] Configurando cantina...")
        await conn.execute(text("""
            INSERT INTO cantina_config (id, aberta, horario_abertura, horario_fechamento, dias_funcionamento, prazo_pedido_minutos, prazo_cancelamento_minutos, observacoes, updated_at)
            VALUES (:id, true, '07:00', '17:00', 'seg,ter,qua,qui,sex', 30, 15, 'Cantina escolar aberta em dias úteis', :now)
            ON CONFLICT DO NOTHING
        """), {"id": uuid.uuid4(), "now": now})
        print("   Cantina: aberta, seg-sex 07:00-17:00, prazo 30min")

        # ── 4. Create products ────────────────────────────────
        print("\n[4/8] Criando produtos...")
        product_ids = []
        for p in PRODUCTS:
            pid = uuid.uuid4()
            product_ids.append({"id": pid, "preco": Decimal(str(p["preco"])), "estoque": p["estoque"], "nome": p["nome"]})
            validade = (now + timedelta(days=random.randint(5, 30))) if p["perecivel"] else None
            await conn.execute(text("""
                INSERT INTO produtos (id, nome, descricao, preco, categoria, estoque_atual, estoque_minimo, codigo, custo, unidade_medida, perecivel, data_validade, ativo, created_at, updated_at)
                VALUES (:id, :nome, :descricao, :preco, :categoria, :estoque, :minimo, :codigo, :custo, 'un', :perecivel, :validade, true, :now, :now)
            """), {
                "id": pid, "nome": p["nome"], "descricao": p["descricao"],
                "preco": Decimal(str(p["preco"])), "categoria": p["categoria"],
                "estoque": p["estoque"], "minimo": p["minimo"],
                "codigo": p["codigo"], "custo": Decimal(str(p["custo"])),
                "perecivel": p["perecivel"], "validade": validade, "now": now,
            })
        print(f"   {len(PRODUCTS)} produtos criados (5 categorias)")

        # ── 5. Create stock movements ─────────────────────────
        print("\n[5/8] Registrando movimentações de estoque...")
        for pid_info in product_ids:
            estoque = pid_info["estoque"]
            if estoque > 0:
                await conn.execute(text("""
                    INSERT INTO movimentacoes_estoque (id, produto_id, tipo, quantidade, estoque_anterior, estoque_atual, motivo, usuario_id, created_at)
                    VALUES (:id, :produto_id, 'ENTRADA', :qtd, 0, :estoque, 'Estoque inicial via seed', :usuario_id, :now)
                """), {
                    "id": uuid.uuid4(), "produto_id": pid_info["id"],
                    "qtd": estoque, "estoque": estoque,
                    "usuario_id": CANT_ID, "now": now,
                })
        print(f"   {len(PRODUCTS)} movimentações de entrada registradas")

        # ── 6. Create orders ──────────────────────────────────
        print("\n[6/8] Criando pedidos fictícios...")
        
        statuses = ["PENDENTE", "APROVADO", "EM_PRODUCAO", "PRONTO", "RETIRADO", "CANCELADO"]
        status_weights = [2, 3, 2, 2, 4, 2]  # distribution
        observacoes_list = [
            None, "Sem cebola por favor", "Trocar por suco de maracujá",
            "Emergência - preciso rápido!", "Levar para a sala 5B",
            None, "Não alergia a leite", None, "Consumo direto na cantina",
            None, "Para a cantina - lanche da manhã", None,
        ]

        pedidos_criados = 0
        # Create orders across the last 10 days for variety
        for day_offset in range(10):
            dia = today - timedelta(days=day_offset)
            num_orders = random.randint(3, 8)
            
            for _ in range(num_orders):
                student_id = random.choice(ALL_STUDENT_IDS)
                status = random.choices(statuses, weights=status_weights, k=1)[0]
                
                # Pick 1-3 random products
                num_items = random.randint(1, 3)
                selected_products = random.sample(product_ids, min(num_items, len(product_ids)))
                
                valor_total = Decimal("0")
                items_data = []
                for p in selected_products:
                    qtd = random.randint(1, 3)
                    preco_total = p["preco"] * qtd
                    valor_total += preco_total
                    items_data.append((p["id"], qtd, p["preco"], preco_total))

                pedido_id = uuid.uuid4()
                hora_pedido = datetime(dia.year, dia.month, dia.day,
                    random.randint(7, 16), random.randint(0, 59), tzinfo=timezone.utc)
                
                saldo_debitado = valor_total if status in ("aprovado", "em_producao", "pronto", "retirado") else Decimal("0")
                mov_id = uuid.uuid4() if saldo_debitado > 0 else None
                obs = random.choice(observacoes_list)

                # Insert order
                await conn.execute(text("""
                    INSERT INTO pedidos (id, aluno_id, responsavel_id, status, valor_total, saldo_debitado, movimentacao_id, observacoes, created_at, updated_at)
                    VALUES (:id, :aluno_id, :responsavel_id, :status, :valor, :saldo, :mov_id, :obs, :created_at, :updated_at)
                """), {
                    "id": pedido_id, "aluno_id": student_id,
                    "responsavel_id": RESP_ID, "status": status,
                    "valor": valor_total, "saldo": saldo_debitado,
                    "mov_id": mov_id, "obs": obs,
                    "created_at": hora_pedido,
                    "updated_at": hora_pedido + timedelta(minutes=random.randint(1, 30)),
                })

                # Insert items
                for item_pid, qtd, preco_unit, preco_total in items_data:
                    await conn.execute(text("""
                        INSERT INTO itens_pedido (id, pedido_id, produto_id, quantidade, preco_unitario, preco_total)
                        VALUES (:id, :pedido_id, :produto_id, :quantidade, :preco_unit, :preco_total)
                    """), {
                        "id": uuid.uuid4(), "pedido_id": pedido_id,
                        "produto_id": item_pid, "quantidade": qtd,
                        "preco_unit": preco_unit, "preco_total": preco_total,
                    })

                # Create wallet movimentacao for approved+ orders
                if mov_id and saldo_debitado > 0:
                    # Get wallet for student
                    wallet_result = await conn.execute(text(
                        "SELECT id, saldo FROM wallets WHERE aluno_id = :sid"
                    ), {"sid": student_id})
                    wallet_row = wallet_result.fetchone()
                    if wallet_row:
                        wallet_id = wallet_row[0]
                        saldo_anterior = wallet_row[1]
                        saldo_posterior = saldo_anterior - saldo_debitado
                        await conn.execute(text("""
                            INSERT INTO movimentacoes (id, wallet_id, tipo, valor, saldo_anterior, saldo_posterior, descricao, criado_por, created_at)
                            VALUES (:id, :wallet_id, 'CONSUMO', :valor, :anterior, :posterior, :desc, :criado_por, :created_at)
                        """), {
                            "id": mov_id, "wallet_id": wallet_id,
                            "valor": saldo_debitado, "anterior": saldo_anterior,
                            "posterior": saldo_posterior,
                            "desc": f"Cantina - Pedido #{str(pedido_id)[:8]}",
                            "criado_por": RESP_ID, "created_at": hora_pedido,
                        })
                        # Update wallet balance
                        await conn.execute(text("""
                            UPDATE wallets SET saldo = saldo - :valor, updated_at = :now WHERE id = :wid
                        """), {"valor": saldo_debitado, "now": now, "wid": wallet_id})

                pedidos_criados += 1

        print(f"   {pedidos_criados} pedidos criados (últimos 10 dias)")
        print(f"   Status: pendente/aprovado/em_producao/pronto/retirado/cancelado")

        # ── 7. Create direct consumption (consumo_direto) ─────
        print("\n[7/8] Criando consumos diretos...")
        consumo_count = 0
        for day_offset in range(7):
            dia = today - timedelta(days=day_offset)
            num_consumos = random.randint(2, 5)
            
            for _ in range(num_consumos):
                student_id = random.choice(ALL_STUDENT_IDS)
                selected = random.sample(product_ids, random.randint(1, 2))
                
                valor_total = Decimal("0")
                items_data = []
                for p in selected:
                    qtd = 1
                    preco_total = p["preco"] * qtd
                    valor_total += preco_total
                    items_data.append((p["id"], qtd, p["preco"], preco_total))

                pedido_id = uuid.uuid4()
                hora = datetime(dia.year, dia.month, dia.day,
                    random.randint(7, 16), random.randint(0, 59), tzinfo=timezone.utc)

                await conn.execute(text("""
                    INSERT INTO pedidos (id, aluno_id, responsavel_id, status, valor_total, saldo_debitado, movimentacao_id, observacoes, created_at, updated_at)
                    VALUES (:id, :aluno_id, :resp_id, 'RETIRADO', :valor, :valor, :mov_id, 'Consumo direto na cantina', :now, :now)
                """), {
                    "id": pedido_id, "aluno_id": student_id,
                    "resp_id": RESP_ID, "valor": valor_total,
                    "mov_id": uuid.uuid4(), "now": hora,
                })

                for item_pid, qtd, preco_unit, preco_total in items_data:
                    await conn.execute(text("""
                        INSERT INTO itens_pedido (id, pedido_id, produto_id, quantidade, preco_unitario, preco_total)
                        VALUES (:id, :pedido_id, :produto_id, :quantidade, :preco_unit, :preco_total)
                    """), {
                        "id": uuid.uuid4(), "pedido_id": pedido_id,
                        "produto_id": item_pid, "quantidade": qtd,
                        "preco_unit": preco_unit, "preco_total": preco_total,
                    })
                consumo_count += 1

        print(f"   {consumo_count} consumos diretos criados")

        # ── 8. Summary ───────────────────────────────────────
        print("\n[8/8] Resumo:")
        result = await conn.execute(text("SELECT COUNT(*) FROM produtos"))
        print(f"   Produtos: {result.scalar()}")
        result = await conn.execute(text("SELECT COUNT(*) FROM pedidos"))
        print(f"   Pedidos: {result.scalar()}")
        result = await conn.execute(text("SELECT COUNT(*) FROM itens_pedido"))
        print(f"   Itens de pedido: {result.scalar()}")
        result = await conn.execute(text("SELECT COUNT(*) FROM movimentacoes_estoque"))
        print(f"   Mov. estoque: {result.scalar()}")
        result = await conn.execute(text("SELECT COUNT(*) FROM movimentacoes"))
        print(f"   Mov. financeiras: {result.scalar()}")
        result = await conn.execute(text("SELECT COUNT(*) FROM wallets"))
        print(f"   Carteiras: {result.scalar()}")
        result = await conn.execute(text("SELECT COUNT(*) FROM alunos"))
        print(f"   Alunos: {result.scalar()}")

        print("\n✅ Seed concluído com sucesso!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
