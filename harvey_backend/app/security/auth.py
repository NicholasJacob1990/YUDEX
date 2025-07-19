"""
Auth stub - Implementação básica de autenticação
"""

from typing import Dict, Any

async def get_api_identity() -> Dict[str, Any]:
    """
    Stub para autenticação - retorna identidade padrão
    TODO: Implementar autenticação real
    """
    return {
        "tenant_id": "default_tenant",
        "user_id": "default_user",
        "permissions": ["read", "write", "admin"]
    }
