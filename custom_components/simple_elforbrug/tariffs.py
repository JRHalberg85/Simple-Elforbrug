"""Simple Elforbrug tariffs handler."""
import logging
from .pyeloverblik.eloverblik import Eloverblik

_LOGGER = logging.getLogger(__name__)

class HassTariff:
    """Wrapper til at hente og gemme tariffer fra Eloverblik."""

    def __init__(self, refresh_token: str, metering_point: str):
        self._client = Eloverblik(refresh_token)
        self._metering_point = metering_point
        self._charges = None

    def update_tariff(self):
        """Hent tariffer fra Eloverblik API."""
        try:
            charges = self._client.get_tariffs(self._metering_point)
            if charges.status == 200:
                self._charges = charges.charges or {}
                _LOGGER.debug("Tariffer hentet: %s", self._charges)
            else:
                _LOGGER.warning("Kunne ikke hente tariffer: %s", charges.detailed_status)
        except Exception as e:
            _LOGGER.exception("Fejl ved hentning af tariffer: %s", e)

    def get_today_tariff(self):
        """
        Returnér den samlede pris for i dag:
        transmissions_nettarif + systemtarif + elafgift.
        """
        if not self._charges:
            return None

        transmissions = self._charges.get("transmissions_nettarif", 0) or 0
        system = self._charges.get("systemtarif", 0) or 0
        elafgift = self._charges.get("elafgift", 0) or 0

        total = transmissions + system + elafgift
        return round(total, 3)

    def get_all_tariffs(self):
        """Returnér alle hentede tariffer med justerede navne og filtreret indhold."""
        if not self._charges:
            return {}

        out = {}
        for key, val in self._charges.items():
            if key.startswith("rabat_på_cerius"):
                continue
            if key == "nettarif_c":
                out["Tariff i dag"] = val
            else:
                out[key] = val
        return out