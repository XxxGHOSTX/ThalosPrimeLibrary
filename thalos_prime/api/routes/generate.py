"""
Generate Routes - Page generation endpoints

Provides deterministic page generation from addresses or queries.
"""

from fastapi import APIRouter, HTTPException
import time

from thalos_prime.models.api_models import (
    GenerateRequest,
    GenerateResponse,
    AddressInfo
)
from thalos_prime.lob_babel_generator import address_to_page, text_to_address, BabelGenerator

router = APIRouter()
generator = BabelGenerator()


@router.post("/", response_model=GenerateResponse)
async def generate_page(request: GenerateRequest):
    """
    Generate a Library of Babel page.
    
    Can generate from an explicit hex address or convert a query to an address.
    
    Args:
        request: Generate request with address or query
    
    Returns:
        GenerateResponse with generated page
    """
    start_time = time.time()
    
    try:
        # Determine address
        if request.address:
            address = request.address
        elif request.query:
            address = text_to_address(request.query)
        else:
            raise HTTPException(status_code=400, detail="Either address or query must be provided")
        
        # Generate page
        page_text = address_to_page(address)
        
        # Validate if requested
        valid = True
        if request.validate:
            is_valid, error = generator.validate_page(page_text)
            valid = is_valid
        
        # Calculate generation time
        generation_time_ms = (time.time() - start_time) * 1000
        
        return GenerateResponse(
            address=AddressInfo(hex_address=address),
            text=page_text,
            valid=valid,
            generation_time_ms=generation_time_ms
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Page generation failed: {str(e)}")


@router.post("/batch")
async def generate_batch(addresses: list[str], validate: bool = True):
    """
    Generate multiple pages in batch.
    
    Args:
        addresses: List of hex addresses
        validate: Whether to validate generated pages
    
    Returns:
        List of generated pages
    """
    if len(addresses) > 100:
        raise HTTPException(status_code=400, detail="Batch size limited to 100 addresses")
    
    results = []
    
    for address in addresses:
        try:
            page_text = address_to_page(address)
            
            valid = True
            if validate:
                is_valid, _ = generator.validate_page(page_text)
                valid = is_valid
            
            results.append({
                'address': address,
                'text': page_text,
                'valid': valid,
                'success': True
            })
        except Exception as e:
            results.append({
                'address': address,
                'error': str(e),
                'success': False
            })
    
    return {
        'total': len(addresses),
        'successful': sum(1 for r in results if r.get('success')),
        'failed': sum(1 for r in results if not r.get('success')),
        'results': results
    }


@router.get("/random")
async def generate_random_page(seed: str = None):
    """
    Generate a random page with optional seed.
    
    Args:
        seed: Optional seed for reproducible randomness
    
    Returns:
        Generated page with random address
    """
    try:
        # Generate random address
        address = generator.generate_random_address(seed=seed)
        
        # Generate page
        page_text = address_to_page(address)
        
        return {
            'address': address,
            'text': page_text,
            'seed': seed,
            'length': len(page_text)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Random generation failed: {str(e)}")


@router.post("/validate")
async def validate_page(address: str, text: str):
    """
    Validate a page against Library of Babel spec.
    
    Args:
        address: Page address
        text: Page text to validate
    
    Returns:
        Validation result
    """
    try:
        is_valid, error = generator.validate_page(text)
        
        return {
            'address': address,
            'valid': is_valid,
            'error': error if not is_valid else None,
            'length': len(text),
            'expected_length': generator.PAGE_LENGTH
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
