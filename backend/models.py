from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BeneficiaryCreate(BaseModel):
    tag_no: str
    farmer_name: str
    father_husband_name: str
    village: str
    district: str
    cattle_feed_kg: int = 0
    silage_kg: int = 0
    mineral_mixture_kg: int = 0

class BeneficiaryInDB(BeneficiaryCreate):
    id: str = Field(alias="_id")

class DeliveryCreate(BaseModel):
    tag_no: str
    partner_name: str
    partner_photo_url: str
    receiver_photo_url: str
    items_photo_url: str
    video_proof_url: str
    status: str = "delivered"

class DeliveryInDB(DeliveryCreate):
    id: str = Field(alias="_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class DeliveryUpdateStatus(BaseModel):
    status: str

class PartnerLogin(BaseModel):
    district: str
    village: str
    supervisor_name: str
    partner_name: str

class SupervisorCreate(BaseModel):
    name: str
    districts: list[str]
    villages: list[str]

class SupervisorInDB(SupervisorCreate):
    id: str = Field(alias="_id")
