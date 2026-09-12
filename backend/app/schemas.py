"""Pydantic giriş/çıkış şemaları (API sözleşmesi)."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class FactoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    role: str
    city: str
    lat: float
    lon: float
    reputation: float


class BatchIn(BaseModel):
    """Yeni DMP oluşturma girdisi."""
    factory_id: int
    city: str
    lat: float
    lon: float
    pamuk: float = Field(ge=0, le=100)
    polyester: float = Field(ge=0, le=100)
    elastan: float = Field(ge=0, le=100)
    kumas: str
    gramaj: int = Field(gt=0)
    en_m: float = Field(gt=0)
    miktar_kg: float = Field(gt=0)
    kalite: str = Field(pattern="^[ABC]$")
    min_fiyat: float = Field(gt=0)
    depo_gun: int = 0
    dogrulanmis: bool = False
    waste_code: str = "04 02 22"


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    factory_id: int
    city: str
    lat: float
    lon: float
    pamuk: float
    polyester: float
    elastan: float
    kumas: str
    gramaj: int
    en_m: float
    miktar_kg: float
    kalite: str
    # min_fiyat (satıcının kör-teklif rezervi) API'de AÇILMAZ — bilinçli gizli.
    depo_gun: int
    dogrulanmis: bool
    reputation: float
    waste_code: str
    status: str
    inconsistencies: list[str] | None = None
    created_at: datetime


class DemandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    buyer: str
    city: str
    lat: float
    lon: float
    min_pamuk: float
    max_elastan: float
    ihtiyac_kg: float
    max_fiyat: float
    min_kalite: str
    dogrulanmis_ister: bool


class MatchOut(BaseModel):
    batch_code: str
    batch_id: int
    score: float
    components: dict[str, float]
    contributions: dict[str, float]
    distance_km: float
    consistent: bool
    explanation: str
    labels: dict[str, str] | None = None


class InconsistencyOut(BaseModel):
    batch_code: str
    inconsistencies: list[str]
    consistent: bool


class DashboardOut(BaseModel):
    dataset: str
    factories: int
    batches: int
    demands: int
    matched: int
    match_rate_pct: float
    routed_tonnes: float
    absorbed_tonnes: float
    co2_tonnes_conservative: float
    co2_tonnes_ecoinvent: float
    water_million_l: float
    avg_score_pct: float
    min_score_pct: float
    max_score_pct: float
    avg_distance_km: float
    inconsistencies_flagged: int
    assumptions: dict


class SeedResult(BaseModel):
    dataset: str
    factories: int
    batches: int
    demands: int
    message: str


# --- Ticari zincir (Dalga 2) -------------------------------------------------
class TradeOpenIn(BaseModel):
    batch_code: str
    demand_code: str


class BidIn(BaseModel):
    by_role: str = Field(pattern="^(buyer|seller)$")
    kind: str = Field(pattern="^(bid|counter|accept|reject)$")
    amount: float = Field(gt=0)              # TL/kg
    qty_kg: float = Field(gt=0)
    note: str | None = None


class DeliverIn(BaseModel):
    """Teslimde gözlenen değerler (beyanla karşılaştırılır)."""
    pamuk: float | None = None
    polyester: float | None = None
    elastan: float | None = None
    kumas: str | None = None
    gramaj: int | None = None
    kalite: str | None = Field(default=None, pattern="^[ABC]$")  # boş string reddedilir
    miktar_kg: float | None = None
    photo_ref: str | None = None             # yüklenen teslim fotoğrafı referansı


class DisputeIn(BaseModel):
    reason: str


class ResolveIn(BaseModel):
    outcome: str = Field(pattern="^(release|refund)$")
    note: str | None = None


class BidOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    by_role: str
    kind: str
    amount: float
    qty_kg: float
    note: str | None = None
    created_at: datetime


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    batch_id: int
    demand_id: int
    status: str
    agreed_price: float | None = None
    agreed_qty_kg: float | None = None
    created_at: datetime
    updated_at: datetime
