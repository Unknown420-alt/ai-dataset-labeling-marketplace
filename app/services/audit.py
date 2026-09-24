from app.models.audit import AuditLog


async def log_action(
    db, user_id: int, action: str, target_type: str, target_id=None, detail=None
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
