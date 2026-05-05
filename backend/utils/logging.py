from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.prediction import AuditLog

async def log_action(
    db: AsyncSession,
    user_id: str,
    action: str,
    resource: str = None,
    details: str = None,
    ip_address: str = None
):
    """
    Log a system action into the audit_logs table.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    # We don't commit here, we let the calling function commit along with its transaction
