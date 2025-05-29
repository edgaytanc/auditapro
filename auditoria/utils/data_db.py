import logging
from typing import Dict, Any, List, Optional
from django.db.models import QuerySet
from auditoria.models import BalanceCuentas, RegistroAuxiliar, SaldoInicial

logger = logging.getLogger(__name__)

def get_balance_data(audit_id: int) -> Dict[str, Any]:
    """
    Obtiene los datos de balance para una auditoría específica
    """
    try:
        # Obtener datos de BalanceCuentas
        balances = BalanceCuentas.objects.filter(audit_id=audit_id)
        
        return {
            'balances': balances,
            'total_balances': balances.count()
        }
    except Exception as e:
        logger.error(f"Error al obtener datos de balance: {str(e)}")
        logger.exception(e)
        return {'balances': [], 'total_balances': 0}

def get_auxiliary_records(audit_id: int) -> Dict[str, Any]:
    """
    Obtiene los registros auxiliares para una auditoría específica
    """
    try:
        # Obtener datos de RegistroAuxiliar
        registros = RegistroAuxiliar.objects.filter(audit_id=audit_id)
        
        return {
            'registros': registros,
            'total_registros': registros.count()
        }
    except Exception as e:
        logger.error(f"Error al obtener registros auxiliares: {str(e)}")
        logger.exception(e)
        return {'registros': [], 'total_registros': 0}

def get_initial_balances(audit_id: int) -> Dict[str, Any]:
    """
    Obtiene los saldos iniciales para una auditoría específica
    """
    try:
        # Obtener datos de SaldoInicial
        saldos = SaldoInicial.objects.filter(audit_id=audit_id)
        
        return {
            'saldos': saldos,
            'total_saldos': saldos.count()
        }
    except Exception as e:
        logger.error(f"Error al obtener saldos iniciales: {str(e)}")
        logger.exception(e)
        return {'saldos': [], 'total_saldos': 0}

def _serialize_balance(balance: BalanceCuentas) -> Dict[str, Any]:
    """
    Serializa un objeto BalanceCuentas a un diccionario
    """
    return {
        'id': balance.id,
        'tipo_balance': balance.tipo_balance,
        'fecha_corte': balance.fecha_corte.isoformat() if balance.fecha_corte else None,
        'seccion': balance.seccion,
        'nombre_cuenta': balance.nombre_cuenta,
        'valor': float(balance.valor) if balance.valor else 0,
        'audit_id': balance.audit_id
    }

def _serialize_registro_auxiliar(registro: RegistroAuxiliar) -> Dict[str, Any]:
    """
    Serializa un objeto RegistroAuxiliar a un diccionario
    """
    return {
        'id': registro.id,
        'cuenta': registro.cuenta,
        'saldo': float(registro.saldo) if registro.saldo else 0,
        'audit_id': registro.audit_id
    }

def _serialize_saldo_inicial(saldo: SaldoInicial) -> Dict[str, Any]:
    """
    Serializa un objeto SaldoInicial a un diccionario
    """
    return {
        'id': saldo.id,
        'cuenta': saldo.cuenta,
        'saldo': float(saldo.saldo) if saldo.saldo else 0,
        'fecha_corte': saldo.fecha_corte.isoformat() if saldo.fecha_corte else None,
        'audit_id': saldo.audit_id
    }

def organize_financial_data(financial_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """
    Organiza los datos financieros en diccionarios indexados por claves específicas:
    - Balances: tipo_balance-fecha_corte-seccion-nombre_cuenta
    - Registros auxiliares: nombre_cuenta
    - Saldos iniciales: nombre_cuenta-fecha_corte
    
    Args:
        financial_data: Diccionario con los datos financieros serializados
        
    Returns:
        Diccionario con los datos organizados por claves específicas
    """
    organized_data = {
        'balances': {},
        'registros_auxiliares': {},
        'saldos_iniciales': {}
    }
    
    # Organizar balances
    for balance in financial_data['balances']:
        key = f"{balance['tipo_balance']}-{balance['fecha_corte']}-{balance['seccion']}-{balance['nombre_cuenta']}"
        organized_data['balances'][key] = balance['valor']
    
    # Organizar registros auxiliares
    for registro in financial_data['registros_auxiliares']:
        key = f"{registro['cuenta']}"
        organized_data['registros_auxiliares'][key] = registro['saldo']
    
    # Organizar saldos iniciales
    for saldo in financial_data['saldos_iniciales']:
        key = f"{saldo['cuenta']}-{saldo['fecha_corte']}"
        organized_data['saldos_iniciales'][key] = saldo['saldo']
    
    return organized_data

def get_all_financial_data(audit_id: int) -> Dict[str, Any]:
    """
    Obtiene todos los datos financieros para una auditoría específica
    y los devuelve en formato JSON serializable
    """
    # Obtener datos de las tres tablas
    balance_data = get_balance_data(audit_id)
    auxiliary_data = get_auxiliary_records(audit_id)
    initial_data = get_initial_balances(audit_id)
    
    # Serializar los datos a formato JSON
    serialized_balances = [_serialize_balance(b) for b in balance_data['balances']]
    serialized_registros = [_serialize_registro_auxiliar(r) for r in auxiliary_data['registros']]
    serialized_saldos = [_serialize_saldo_inicial(s) for s in initial_data['saldos']]
    
    # Datos serializados
    serialized_data = {
        'balances': serialized_balances,
        'registros_auxiliares': serialized_registros,
        'saldos_iniciales': serialized_saldos,
    }
    
    # Organizar datos por claves específicas
    organized_data = organize_financial_data(serialized_data)
    
    return {
        'raw': serialized_data,
        'organized': organized_data
    }