import uuid
from datetime import date, datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


recipe_categories = Table(
    "recipe_categories",
    Base.metadata,
    Column("recipe_id", UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)

recipe_tags = Table(
    "recipe_tags",
    Base.metadata,
    Column("recipe_id", UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

# Favorito por utilizador (evolução do favorito único do workspace da v1.1 —
# ver as regras de privacidade). Tabela de associação simples, sem relationship() ORM para
# User: `app/crud.py` consulta-a diretamente e marca `Recipe.is_favorite`
# (atributo Python, já não coluna) por pedido, para o schema/frontend não
# mudarem — só o significado passa de "favorito do agregado" a "favorito
# deste utilizador".
recipe_favorites = Table(
    "recipe_favorites",
    Base.metadata,
    Column("recipe_id", UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

# Cookbooks/coleções (v2): lista manual
# Uma receita pertence a uma coleção explícita, não a um filtro inteligente —
# pode estar em várias coleções, sem filtro automático.
cookbook_recipes = Table(
    "cookbook_recipes",
    Base.metadata,
    Column("cookbook_id", UUID(as_uuid=True), ForeignKey("cookbooks.id", ondelete="CASCADE"), primary_key=True),
    Column("recipe_id", UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    cookbooks: Mapped[list["Cookbook"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    meal_plan_entries: Mapped[list["MealPlanEntry"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    meal_plan_templates: Mapped[list["MealPlanTemplate"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    meal_plan_recurrences: Mapped[list["MealPlanRecurrence"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    shopping_list_items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    pantry_items: Mapped[list["PantryItem"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    dietary_profiles: Mapped[list["DietaryProfile"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    ingredient_substitutions: Mapped[list["IngredientSubstitution"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Conta de utilizador (fastapi-users) — `id`/`email`/`hashed_password`/
    `is_active`/`is_superuser`/`is_verified` vêm do mixin
    `SQLAlchemyBaseUserTableUUID`. Só é consultada pelo motor assíncrono
    (`app/auth.py`) — `fastapi_users_db_sqlalchemy` exige `AsyncSession`,
    sem variante síncrona (verificado no código-fonte da lib,
    decisão #1). O resto da app (workspace_members incluído) continua a
    usar o `Session` síncrono de sempre — é a mesma tabela, só acedida por
    dois motores diferentes."""

    __tablename__ = "users"

    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    oidc_identities: Mapped[list["OIDCIdentity"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class OIDCIdentity(Base):
    __tablename__ = "oidc_identities"
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="uq_oidc_identity_issuer_subject"),
        UniqueConstraint("user_id", "issuer", name="uq_oidc_identity_user_issuer"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    issuer: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="oidc_identities")


class WorkspaceMember(Base):
    """Liga um User a um Workspace. Sem coluna de papel/role — ao
    contrário do Securo (owner/editor/viewer, várias workspaces por
    utilizador), o Tacho tem duas pessoas e uma única workspace, para
    sempre; qualquer membro tem acesso total."""

    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="members")


class DietaryProfile(Base):
    __tablename__ = "dietary_profiles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(Text)
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    intolerances: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="dietary_profiles")


class IngredientSubstitution(Base):
    __tablename__ = "ingredient_substitutions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    ingredient_name: Mapped[str] = mapped_column(Text)
    substitute_name: Mapped[str] = mapped_column(Text)
    quantity_ratio: Mapped[float | None] = mapped_column(Numeric(8, 3))
    note: Mapped[str | None] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="ingredient_substitutions")


class Recipe(Base):
    __tablename__ = "recipes"
    # Índice GIN criado via op.execute na migração f8210117be6a; registado
    # aqui só para o autogenerate parar de o assinalar como "removido" em
    # todas as migrações seguintes (já aconteceu duas vezes — 2fbf5b821d94
    # e 4d0d5fd85a2d tiveram de remover um op.drop_index espúrio à mão).
    # O CHECK do rating (migração 1124746a9f09) tinha o mesmo problema —
    # declarado agora para não repetir pela sexta vez.
    __table_args__ = (
        Index(
            "ix_recipes_title_tsv",
            text("to_tsvector('portuguese', title)"),
            postgresql_using="gin",
        ),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_recipes_rating_range"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    servings: Mapped[int | None]
    prep_minutes: Mapped[int | None]
    cook_minutes: Mapped[int | None]
    source_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # Caminho relativo a Settings.images_dir — "receitas/<este id>/<uuid4>.ext"
    # (app/images.py), servido em /images/{image_path}; nunca o caminho
    # absoluto do disco. Registos antigos, de antes desta organização por
    # pastas, podem ainda ter só o nome do ficheiro (sem "/") — também
    # funciona, StaticFiles serve os dois na mesma.
    image_path: Mapped[str | None] = mapped_column(Text)
    source_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="SET NULL")
    )
    # Informação nutricional por porção, entrada manual —
    # `app/nutrition.py` pode sugerir valores (Open Food Facts), mas nunca
    # grava sozinho, só por confirmação explícita no formulário.
    calories_kcal: Mapped[int | None]
    protein_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    carbs_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    fat_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    # Custo estimado da receita TOTAL (não por porção) — entrada manual, sem
    # fonte de preços automática disponível. Custo por porção
    # calculado em runtime no frontend (estimated_cost / servings).
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(8, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Marcado ao concluir o Modo Cozinha.
    last_made_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Avaliação por estrelas (1-5) — do agregado, não por utilizador
    # (ao contrário de is_favorite;
    # que não tem esta funcionalidade). Validação do intervalo em
    # schemas.py + CHECK "ck_recipes_rating_range" (criado na migração
    # 1124746a9f09, declarado no __table_args__ acima desde a migração
    # 90e07c148e15 — antes disso o autogenerate propunha removê-lo por
    # engano em todas as migrações seguintes, mesmo problema do índice GIN).
    rating: Mapped[int | None]
    # Partilha pública temporária (QR/link, sem autenticação) — gerado a
    # pedido em POST /recipes/{id}/share, válido 5h a partir desse pedido
    # (pedir de novo renova a janela), nunca ligado por omissão. Token
    # aleatório (secrets.token_urlsafe), não o id da receita, para nunca
    # expor um uuid interno num link externo; GET /public/recipes/{token}
    # confere expires_at antes de devolver qualquer dado.
    share_token: Mapped[str | None] = mapped_column(Text, unique=True)
    share_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # `is_favorite` NÃO é uma coluna — `app/crud.py` marca este atributo em
    # runtime consultando `recipe_favorites` para o utilizador do pedido
    # (ver comentário nessa tabela). Sem tipo declarado aqui de propósito;
    # só existe depois de passar por `_annotate_favorites`.

    workspace: Mapped["Workspace"] = relationship(back_populates="recipes")
    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="Ingredient.position"
    )
    steps: Mapped[list["Step"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="Step.position"
    )
    categories: Mapped[list["Category"]] = relationship(secondary=recipe_categories, back_populates="recipes")
    tags: Mapped[list["Tag"]] = relationship(secondary=recipe_tags, back_populates="recipes")
    cookbooks: Mapped[list["Cookbook"]] = relationship(secondary=cookbook_recipes, back_populates="recipes")
    cook_notes: Mapped[list["CookNote"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="CookNote.created_at.desc()"
    )
    cook_history: Mapped[list["CookHistoryEntry"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="CookHistoryEntry.made_at.desc()"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="Comment.created_at.asc()"
    )
    images: Mapped[list["RecipeImage"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeImage.position"
    )


class RecipeImage(Base):
    """Galeria de fotos extra da receita — separada de `Recipe.image_path`
    de propósito (a foto principal, mostrada em todo o lado — card, hero do
    Detalhe — continua exatamente como estava, upload único via
    RecipeForm.tsx). `is_cover` marca qual desta galeria aparece primeiro,
    mas nunca substitui `image_path`."""

    __tablename__ = "recipe_images"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(Text)
    position: Mapped[int]
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    recipe: Mapped["Recipe"] = relationship(back_populates="images")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    position: Mapped[int]
    name: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[str | None] = mapped_column(Text)
    is_header: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    position: Mapped[int]
    instruction: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int | None]

    recipe: Mapped["Recipe"] = relationship(back_populates="steps")


class CookNote(Base):
    """Nota rápida opcional ao concluir o Modo Cozinha — histórico
    com data, não um campo único sobrescrevível (esse já existe como
    Recipe.notes, editável no formulário; conceito diferente)."""

    __tablename__ = "cook_notes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    cook_history_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cook_history.id", ondelete="SET NULL")
    )
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped["Recipe"] = relationship(back_populates="cook_notes")


class CookHistoryEntry(Base):
    __tablename__ = "cook_history"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    made_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped["Recipe"] = relationship(back_populates="cook_history")


class Comment(Base):
    """Comentário livre por receita, com autor — diferente do `CookNote`
    (nota pós-confeção, sem autor, ligada ao Modo Cozinha) e de
    `Recipe.notes` (campo único editável). Qualquer membro pode apagar
    qualquer comentário (mesmo modelo de confiança total do resto da app —
    ver `DELETE /workspace/members/{id}`, sem admin/roles)."""

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped["Recipe"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship()

    @property
    def author_name(self) -> str | None:
        return self.user.name

    @property
    def author_email(self) -> str:
        return self.user.email


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_category_workspace_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(Text)

    workspace: Mapped["Workspace"] = relationship(back_populates="categories")
    recipes: Mapped[list["Recipe"]] = relationship(secondary=recipe_categories, back_populates="categories")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_tag_workspace_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)

    workspace: Mapped["Workspace"] = relationship(back_populates="tags")
    recipes: Mapped[list["Recipe"]] = relationship(secondary=recipe_tags, back_populates="tags")


class Cookbook(Base):
    """Coleção manual de receitas (v2) — sem
    UniqueConstraint de nome ao contrário de Category/Tag, porque não há
    razão de produto para proibir duas coleções com o mesmo nome (ex. duas
    pessoas a fazerem "Favoritas de Verão" em anos diferentes)."""

    __tablename__ = "cookbooks"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="cookbooks")
    recipes: Mapped[list["Recipe"]] = relationship(secondary=cookbook_recipes, back_populates="cookbooks")


class MealPlanEntry(Base):
    """Uma receita atribuída a um período de refeição de um dia. A
    ausência de linha para um dia/refeição é o estado "vazio" — não há um
    valor nulo de receita, atribuir outra substitui a linha (upsert) e
    remover apaga-a. Coluna chama-se `day`, não `date`, para não sombrear o
    tipo `date` importado do datetime na anotação da classe."""

    __tablename__ = "meal_plan_entries"
    __table_args__ = (UniqueConstraint("workspace_id", "day", "meal_type", name="uq_meal_plan_slot"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    # O período é texto simples, sem enum na BD, consistente com o
    # resto do modelo (nenhuma outra tabela usa enum do Postgres).
    meal_type: Mapped[str] = mapped_column(Text)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="meal_plan_entries")
    recipe: Mapped["Recipe"] = relationship()


class MealPlanTemplate(Base):
    __tablename__ = "meal_plan_templates"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_meal_plan_template_workspace_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    slots: Mapped[list[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="meal_plan_templates")


class MealPlanRecurrence(Base):
    __tablename__ = "meal_plan_recurrences"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_meal_plan_recurrence_weekday"),
        CheckConstraint("interval_weeks >= 1", name="ck_meal_plan_recurrence_interval"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    weekday: Mapped[int]
    meal_type: Mapped[str] = mapped_column(Text)
    interval_weeks: Mapped[int] = mapped_column(default=1, server_default="1")
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    workspace: Mapped["Workspace"] = relationship(back_populates="meal_plan_recurrences")
    recipe: Mapped["Recipe"] = relationship()


class ShoppingListItem(Base):
    """Item da lista de compras do workspace — sem semana/data associada,
    é sempre "a lista atual". `quantity`
    é texto livre já composto (ex. "500 g"), não número+unidade separados,
    porque agrega quantidades de várias receitas/refeições sem conversão de
    unidades (fora de âmbito — ver nota em crud.generate_shopping_list)."""

    __tablename__ = "shopping_list_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    quantity: Mapped[str | None] = mapped_column(Text)
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="shopping_list_items")


class PantryItem(Base):
    """Produto disponível no agregado, com stock e validade opcionais.
    Alimenta o filtro "Dá para fazer" (crud.py::
    list_recipes, makeable_only) por correspondência de substring
    normalizada (sem acentos) contra o nome dos ingredientes."""

    __tablename__ = "pantry_items"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_pantry_item_workspace_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    has_it: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[str | None] = mapped_column(Text)
    expires_on: Mapped[date | None] = mapped_column(Date)
    minimum_quantity: Mapped[float | None] = mapped_column(Numeric(10, 2))

    workspace: Mapped["Workspace"] = relationship(back_populates="pantry_items")
