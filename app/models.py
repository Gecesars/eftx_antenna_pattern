from __future__ import annotations

import enum
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Iterable

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


class SexEnum(enum.Enum):
    MALE = "M"
    FEMALE = "F"
    NON_BINARY = "X"


class PatternType(enum.StrEnum):
    HRP = "HRP"
    VRP = "VRP"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BaseModel(db.Model):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(TimestampMixin, BaseModel, UserMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sex: Mapped[SexEnum | None] = mapped_column(Enum(SexEnum), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    address_line: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str | None] = mapped_column(String(64))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    country: Mapped[str | None] = mapped_column(String(64))
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True)
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)
    cnpj_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String(16), default="user", index=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    assistant_conversation: Mapped["AssistantConversation | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def get_id(self) -> str:  # pragma: no cover - flask-login contract
        return str(self.id)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Antenna(TimestampMixin, BaseModel):
    __tablename__ = "antennas"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    model_number: Mapped[str | None] = mapped_column(String(64), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    nominal_gain_dbd: Mapped[float] = mapped_column(Float, default=0.0)
    polarization: Mapped[str | None] = mapped_column(String(32))
    frequency_min_mhz: Mapped[float | None] = mapped_column(Float)
    frequency_max_mhz: Mapped[float | None] = mapped_column(Float)

    patterns: Mapped[list["AntennaPattern"]] = relationship(
        back_populates="antenna",
        cascade="all, delete-orphan",
        order_by="AntennaPattern.pattern_type",
    )
    project_links: Mapped[list["ProjectAntenna"]] = relationship(back_populates="antenna")

    def pattern_for(self, pattern_type: PatternType) -> "AntennaPattern | None":
        for pattern in self.patterns:
            if pattern.pattern_type == pattern_type:
                return pattern
        return None


class AntennaPattern(TimestampMixin, BaseModel):
    __tablename__ = "antenna_patterns"
    __table_args__ = (UniqueConstraint("antenna_id", "pattern_type", name="uq_pattern_type"),)

    antenna_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("antennas.id", ondelete="CASCADE"), nullable=False)
    pattern_type: Mapped[PatternType] = mapped_column(Enum(PatternType), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    antenna: Mapped["Antenna"] = relationship(back_populates="patterns")
    points: Mapped[list["AntennaPatternPoint"]] = relationship(
        back_populates="pattern",
        cascade="all, delete-orphan",
        order_by="AntennaPatternPoint.angle_deg",
    )

    @property
    def angles_deg(self) -> list[float]:
        return [point.angle_deg for point in self.points]

    @property
    def amplitudes_linear(self) -> list[float]:
        return [point.amplitude_linear for point in self.points]

    def replace_points(self, angles: Iterable[float], amplitudes: Iterable[float]) -> None:
        angle_list = [float(value) for value in angles]
        amp_list = [max(0.0, float(value)) for value in amplitudes]
        if len(angle_list) != len(amp_list):
            raise ValueError("Angles and amplitudes must have matching lengths.")
        key_precision = 6
        unique: "OrderedDict[float, tuple[float, float]]" = OrderedDict()
        for angle, amplitude in zip(angle_list, amp_list):
            key = round(angle, key_precision)
            unique[key] = (float(angle), float(amplitude))
        self.points.clear()
        for angle, amplitude in unique.values():
            self.points.append(AntennaPatternPoint(angle_deg=angle, amplitude_linear=amplitude))


class AntennaPatternPoint(TimestampMixin, BaseModel):
    __tablename__ = "antenna_pattern_points"
    __table_args__ = (
        UniqueConstraint("pattern_id", "angle_deg", name="uq_pattern_point"),
        Index("ix_pattern_point_order", "pattern_id", "angle_deg"),
    )

    pattern_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("antenna_patterns.id", ondelete="CASCADE"), nullable=False, index=True)
    angle_deg: Mapped[float] = mapped_column(Float, nullable=False)
    amplitude_linear: Mapped[float] = mapped_column(Float, nullable=False)

    pattern: Mapped["AntennaPattern"] = relationship(back_populates="points")


class Project(TimestampMixin, BaseModel):
    __tablename__ = "projects"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    frequency_mhz: Mapped[float] = mapped_column(Float, nullable=False)
    tx_power_w: Mapped[float] = mapped_column(Float, nullable=False)
    tower_height_m: Mapped[float] = mapped_column(Float, nullable=False)
    cable_type: Mapped[str | None] = mapped_column(String(120))
    cable_length_m: Mapped[float] = mapped_column(Float, default=0.0)
    splitter_loss_db: Mapped[float] = mapped_column(Float, default=0.0)
    connector_loss_db: Mapped[float] = mapped_column(Float, default=0.0)
    vswr_target: Mapped[float] = mapped_column(Float, default=1.5)
    notes: Mapped[str | None] = mapped_column(Text)

    v_count: Mapped[int] = mapped_column(Integer, default=1)
    v_spacing_m: Mapped[float] = mapped_column(Float, default=0.0)
    v_beta_deg: Mapped[float] = mapped_column(Float, default=0.0)
    v_tilt_deg: Mapped[float] = mapped_column(Float, default=0.0)
    v_level_amp: Mapped[float] = mapped_column(Float, default=1.0)
    v_norm_mode: Mapped[str] = mapped_column(String(16), default="max")

    h_count: Mapped[int] = mapped_column(Integer, default=1)
    h_spacing_m: Mapped[float] = mapped_column(Float, default=0.0)
    h_beta_deg: Mapped[float] = mapped_column(Float, default=0.0)
    h_step_deg: Mapped[float] = mapped_column(Float, default=0.0)
    h_level_amp: Mapped[float] = mapped_column(Float, default=1.0)
    h_norm_mode: Mapped[str] = mapped_column(String(16), default="max")

    feeder_loss_db: Mapped[float] = mapped_column(Float, default=0.0)
    composition_meta: Mapped[dict | None] = mapped_column(JSONB)

    owner: Mapped["User"] = relationship(back_populates="projects")
    antennas: Mapped[list["ProjectAntenna"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectAntenna.position_index",
    )
    revisions: Mapped[list["ProjectExport"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

    @property
    def primary_antenna_link(self) -> "ProjectAntenna | None":
        return self.antennas[0] if self.antennas else None

    @property
    def antenna(self) -> "Antenna | None":
        link = self.primary_antenna_link
        return link.antenna if link else None

    @antenna.setter
    def antenna(self, antenna: "Antenna | None") -> None:
        if antenna is None:
            self.antennas.clear()
            return
        if self.antennas:
            self.antennas[0].antenna = antenna
        else:
            self.antennas.append(
                ProjectAntenna(
                    antenna=antenna,
                    position_index=0,
                )
            )


class ProjectAntenna(TimestampMixin, BaseModel):
    __tablename__ = "project_antennas"
    __table_args__ = (
        UniqueConstraint("project_id", "position_index", name="uq_project_slot"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    antenna_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("antennas.id", ondelete="RESTRICT"), nullable=False, index=True)
    position_index: Mapped[int] = mapped_column(Integer, default=0)
    spacing_m: Mapped[float] = mapped_column(Float, default=0.0)
    phase_deg: Mapped[float] = mapped_column(Float, default=0.0)
    amplitude_linear: Mapped[float] = mapped_column(Float, default=1.0)
    tilt_deg: Mapped[float] = mapped_column(Float, default=0.0)
    details: Mapped[dict | None] = mapped_column("metadata", JSONB)

    project: Mapped["Project"] = relationship(back_populates="antennas")
    antenna: Mapped["Antenna"] = relationship(back_populates="project_links")


class ProjectExport(TimestampMixin, BaseModel):
    __tablename__ = "project_exports"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    erp_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pat_path: Mapped[str] = mapped_column(String(255), nullable=False)
    prn_path: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(255), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="revisions")


class AssistantConversation(TimestampMixin, BaseModel):
    __tablename__ = "assistant_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(120))

    user: Mapped["User"] = relationship(back_populates="assistant_conversation")
    messages: Mapped[list["AssistantMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at",
    )


class AssistantMessage(TimestampMixin, BaseModel):
    __tablename__ = "assistant_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assistant_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)

    conversation: Mapped["AssistantConversation"] = relationship(back_populates="messages")
