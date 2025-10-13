try:
    from .base import DVRBrand
    from .hikvision import HikvisionBrand
    from .cpplus import CPPlusBrand
except ImportError:
    # Fallback when executed directly without package context
    from brands.base import DVRBrand
    from brands.hikvision import HikvisionBrand
    from brands.cpplus import CPPlusBrand

_BRANDS = {
    'hikvision': HikvisionBrand(),
    'cpplus': CPPlusBrand(),
}

def get_brand(name: str) -> DVRBrand:
    key = (name or '').strip().lower()
    # Fallback: try to infer by name contains
    if 'hik' in key:
        return _BRANDS['hikvision']
    if 'cpplus' in key or 'cp+' in key or 'cp plus' in key:
        return _BRANDS['cpplus']
    # Default to Hikvision-like behavior
    return _BRANDS['hikvision']
