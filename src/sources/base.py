from abc import ABC, abstractmethod
from typing import List
from ..models import SearchConfig, APIKeys, FlightOffer

class FlightSource(ABC):
    @abstractmethod
    def search(self, config: SearchConfig, keys: APIKeys) -> List[FlightOffer]:
        pass
    
    @abstractmethod
    def name(self) -> str:
        pass
