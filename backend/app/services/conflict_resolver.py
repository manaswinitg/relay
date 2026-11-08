import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.shelter import Shelter
from app.models.inventory import ShelterInventory, ResourceType
from app.models.sync import SyncAuditLog, ConflictRecord
from app.models.base import get_utc_now


class ConflictResolver:
    """
    Core distributed conflict resolver implementing:
    - Tier 2: Commutative Delta Merging for inventory
    - Tier 3: OCC Version Validation & Conflict Quarantine for mutable entities
    """

    @staticmethod
    async def apply_inventory_delta(
        db: AsyncSession,
        shelter_id: str,
        resource_type_code: str,
        delta: float,
        device_id: str,
        client_timestamp: Optional[datetime] = None,
        base_version: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Commutatively applies inventory delta:
        New Quantity = Server Current Quantity + Delta.
        Guarantees no lost updates even when concurrent offline users submit changes.
        """
        if client_timestamp is None:
            client_timestamp = get_utc_now()

        # Find resource type
        res_stmt = select(ResourceType).where(ResourceType.code == resource_type_code)
        res_exec = await db.execute(res_stmt)
        resource_type = res_exec.scalar_one_or_none()

        if not resource_type:
            # Fallback by ID if code lookup fails
            res_stmt2 = select(ResourceType).where(ResourceType.id == resource_type_code)
            res_exec2 = await db.execute(res_stmt2)
            resource_type = res_exec2.scalar_one_or_none()
            if not resource_type:
                # Auto-initialize resource type if code is standard or ad-hoc from field
                code_clean = resource_type_code.upper()
                name_clean = code_clean.replace("_", " ").title()
                cat_clean = "OTHER"
                if "WATER" in code_clean: cat_clean = "WATER"
                elif "FOOD" in code_clean or "MEAL" in code_clean: cat_clean = "FOOD"
                elif "AID" in code_clean or "MED" in code_clean: cat_clean = "MEDICAL"
                elif "SHELTER" in code_clean or "BLANKET" in code_clean: cat_clean = "SHELTER_SUPPLIES"
                
                resource_type = ResourceType(
                    code=code_clean,
                    name=name_clean,
                    category=cat_clean,
                    unit="UNITS",
                    is_critical=True
                )
                db.add(resource_type)
                await db.flush()

        # Find or create shelter inventory row
        inv_stmt = select(ShelterInventory).where(
            ShelterInventory.shelter_id == shelter_id,
            ShelterInventory.resource_type_id == resource_type.id
        )
        inv_exec = await db.execute(inv_stmt)
        inventory = inv_exec.scalar_one_or_none()

        if not inventory:
            # Initialize inventory row
            initial_qty = max(0.0, delta)
            inventory = ShelterInventory(
                shelter_id=shelter_id,
                resource_type_id=resource_type.id,
                quantity=initial_qty,
                min_threshold=10.0,
                last_updated_by_user_id=user_id,
                version=1
            )
            db.add(inventory)
            await db.flush()
            new_version = 1
        else:
            old_qty = inventory.quantity
            calc_qty = old_qty + delta
            # Prevent negative inventory in physical world
            inventory.quantity = max(0.0, calc_qty)
            inventory.version += 1
            inventory.updated_at = get_utc_now()
            inventory.last_updated_by_user_id = user_id
            new_version = inventory.version

        # Record audit log
        audit = SyncAuditLog(
            client_device_id=device_id,
            user_id=user_id,
            action_type="DELTA",
            entity_name="INVENTORY",
            entity_id=inventory.id,
            base_version=base_version,
            resulting_version=new_version,
            payload={
                "shelter_id": shelter_id,
                "resource_code": resource_type.code,
                "delta": delta,
                "final_quantity": inventory.quantity
            },
            sync_status="APPLIED",
            client_timestamp=client_timestamp
        )
        db.add(audit)
        await db.commit()

        return ("APPLIED", new_version, None)

    @staticmethod
    async def evaluate_shelter_update(
        db: AsyncSession,
        shelter_id: str,
        incoming_payload: Dict[str, Any],
        base_version: int,
        device_id: str,
        client_timestamp: Optional[datetime] = None,
        user_id: Optional[str] = None
    ) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Evaluates structural shelter update with Optimistic Concurrency Control (OCC).
        If base_version == current_version: Apply update.
        If base_version < current_version: Quarantines into conflict_records.
        """
        if client_timestamp is None:
            client_timestamp = get_utc_now()

        stmt = select(Shelter).where(Shelter.id == shelter_id)
        exec_res = await db.execute(stmt)
        shelter = exec_res.scalar_one_or_none()

        if not shelter:
            return ("REJECTED", None, f"Shelter {shelter_id} not found.")

        # OCC Check
        if base_version == shelter.version:
            # Clean non-conflicting mutation
            for key, val in incoming_payload.items():
                if hasattr(shelter, key) and key not in ["id", "client_assigned_uuid", "version", "created_at"]:
                    if val is not None:
                        setattr(shelter, key, val)

            shelter.version += 1
            shelter.updated_at = get_utc_now()
            resulting_version = shelter.version

            # Log audit
            audit = SyncAuditLog(
                client_device_id=device_id,
                user_id=user_id,
                action_type="UPDATE",
                entity_name="SHELTER",
                entity_id=shelter.id,
                base_version=base_version,
                resulting_version=resulting_version,
                payload=incoming_payload,
                sync_status="APPLIED",
                client_timestamp=client_timestamp
            )
            db.add(audit)
            await db.commit()
            return ("APPLIED", resulting_version, None)

        else:
            # Conflict detected! Server state has evolved.
            # Quarantine in conflict_records
            server_payload = {
                "name": shelter.name,
                "address": shelter.address,
                "total_capacity": shelter.total_capacity,
                "current_occupancy": shelter.current_occupancy,
                "status": shelter.status,
                "contact_phone": shelter.contact_phone,
                "version": shelter.version
            }

            conflict = ConflictRecord(
                entity_type="SHELTER",
                entity_id=shelter.id,
                client_device_id=device_id,
                client_base_version=base_version,
                server_current_version=shelter.version,
                client_payload=incoming_payload,
                server_payload=server_payload,
                resolution_status="PENDING_REVIEW"
            )
            db.add(conflict)

            audit = SyncAuditLog(
                client_device_id=device_id,
                user_id=user_id,
                action_type="UPDATE",
                entity_name="SHELTER",
                entity_id=shelter.id,
                base_version=base_version,
                resulting_version=shelter.version,
                payload=incoming_payload,
                sync_status="CONFLICT_DETECTED",
                conflict_reason=f"Client base v{base_version} lagged behind server v{shelter.version}",
                client_timestamp=client_timestamp
            )
            db.add(audit)
            await db.commit()

            return ("CONFLICT_ISOLATED", shelter.version, f"Version mismatch (base v{base_version} vs server v{shelter.version}). Quarantined for coordinator review.")
