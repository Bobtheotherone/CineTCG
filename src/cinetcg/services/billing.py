from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PurchaseResult:
    ok: bool
    message: str


class BillingProvider(Protocol):
    def purchase(self, product_id: str) -> PurchaseResult: ...

    def restore_purchases(self) -> PurchaseResult: ...


class MockBillingProvider:
    """V1 billing provider: always succeeds.

    Real implementations (StoreKit/Play Billing) can replace this later.
    """

    def purchase(self, product_id: str) -> PurchaseResult:
        return PurchaseResult(ok=True, message=f"Mock purchase successful: {product_id}")

    def restore_purchases(self) -> PurchaseResult:
        return PurchaseResult(ok=True, message="Mock restore complete.")
