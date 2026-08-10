import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
    Column,
    func,
    text,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
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


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    categories: Mapped[list["Category"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    meal_plan_entries: Mapped[list["MealPlanEntry"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    shopping_list_items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Conta de utilizador (fastapi-users) — `id`/`email`/`hashed_password`/
    `is_active`/`is_superuser`/`is_verified` vêm do mixin
    `SQLAlchemyBaseUserTableUUID`. Só é consultada pelo motor assíncrono
    (`app/auth.py`) — `fastapi_users_db_sqlalchemy` exige `AsyncSession`,
    sem variante síncrona (verificado no código-fonte da lib, TODO.md
    decisão #1). O resto da app (workspace_members incluído) continua a
    usar o `Session` síncrono de sempre — é a mesma tabela, só acedida por
    dois motores diferentes."""

    __tablename__ = "users"

    name: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkspaceMember(Base):
    """Liga um User a um Workspace. Sem coluna de papel/role — ao
    contrário do Securo (owner/editor/viewer, várias workspaces por
    utilizador), o Tacho tem duas pessoas e uma única workspace, para
    sempre (decisão #1 do TODO.md); qualquer membro tem acesso total."""

    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="members")


class Recipe(Base):
    __tablename__ = "recipes"
    # Criado via op.execute na migração f8210117be6a; registado aqui só
    # para o autogenerate parar de o assinalar como "removido" em todas as
    # migrações seguintes (já aconteceu duas vezes — 2fbf5b821d94 e
    # 4d0d5fd85a2d tiveram de remover um op.drop_index espúrio à mão).
    __table_args__ = (
        Index(
            "ix_recipes_title_tsv",
            text("to_tsvector('portuguese', title)"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    servings: Mapped[int | None]
    prep_minutes: Mapped[int | None]
    cook_minutes: Mapped[int | None]
    source_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # Só o nome do ficheiro (uuid4 + extensão), guardado em Settings.images_dir
    # e servido em /images/{image_path} — nunca o caminho absoluto do disco.
    image_path: Mapped[str | None] = mapped_column(Text)
    # Informação nutricional por porção, entrada manual (PRD 5.1/11.1 #5).
    # Cálculo automático a partir dos ingredientes fica para a v2 (Open Food
    # Facts, não LLM — ver TODO.md).
    calories_kcal: Mapped[int | None]
    protein_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    carbs_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    fat_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Marcado ao concluir o Modo Cozinha (PRD 5.1, alimenta a métrica M3).
    last_made_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Favorito do Workspace (agregado), não por utilizador — não há contas
    # individuais antes da v1.2 (TODO.md).
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    workspace: Mapped["Workspace"] = relationship(back_populates="recipes")
    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="Ingredient.position"
    )
    steps: Mapped[list["Step"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="Step.position"
    )
    categories: Mapped[list["Category"]] = relationship(secondary=recipe_categories, back_populates="recipes")
    tags: Mapped[list["Tag"]] = relationship(secondary=recipe_tags, back_populates="recipes")
    cook_notes: Mapped[list["CookNote"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", order_by="CookNote.created_at.desc()"
    )


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
    """Nota rápida opcional ao concluir o Modo Cozinha (PRD 5.1) — histórico
    com data, não um campo único sobrescrevível (esse já existe como
    Recipe.notes, editável no formulário; conceito diferente)."""

    __tablename__ = "cook_notes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recipe: Mapped["Recipe"] = relationship(back_populates="cook_notes")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_category_workspace_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text)

    workspace: Mapped["Workspace"] = relationship(back_populates="categories")
    recipes: Mapped[list["Recipe"]] = relationship(secondary=recipe_categories, back_populates="categories")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_tag_workspace_name"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text)

    workspace: Mapped["Workspace"] = relationship(back_populates="tags")
    recipes: Mapped[list["Recipe"]] = relationship(secondary=recipe_tags, back_populates="tags")


class MealPlanEntry(Base):
    """Uma receita atribuída a uma refeição (almoço/jantar) de um dia. A
    ausência de linha para um dia/refeição é o estado "vazio" — não há um
    valor nulo de receita, atribuir outra substitui a linha (upsert) e
    remover apaga-a. Coluna chama-se `day`, não `date`, para não sombrear o
    tipo `date` importado do datetime na anotação da classe."""

    __tablename__ = "meal_plan_entries"
    __table_args__ = (
        UniqueConstraint("workspace_id", "day", "meal_type", name="uq_meal_plan_slot"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    day: Mapped[date] = mapped_column(Date)
    # "almoco" | "jantar" — texto simples, sem enum na BD, consistente com o
    # resto do modelo (nenhuma outra tabela usa enum do Postgres).
    meal_type: Mapped[str] = mapped_column(Text)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="meal_plan_entries")
    recipe: Mapped["Recipe"] = relationship()


class ShoppingListItem(Base):
    """Item da lista de compras do workspace — sem semana/data associada,
    é sempre "a lista atual" (PRD não pede histórico de listas). `quantity`
    é texto livre já composto (ex. "500 g"), não número+unidade separados,
    porque agrega quantidades de várias receitas/refeições sem conversão de
    unidades (fora de âmbito — ver nota em crud.generate_shopping_list)."""

    __tablename__ = "shopping_list_items"

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text)
    quantity: Mapped[str | None] = mapped_column(Text)
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="shopping_list_items")
