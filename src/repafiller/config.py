import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    api_url: str = "https://milankoys.sk/attendance"
    token: str   = os.getenv("REPA_TOKEN", "")
    place: int   = 2
    status: int  = 1