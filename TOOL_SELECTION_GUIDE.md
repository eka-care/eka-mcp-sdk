# Tool Selection Guide for LLMs

This document outlines the paradigms and strategies for guiding LLMs to choose comprehensive tools over basic ones while keeping both available.

## **1. Tool Naming Convention Strategy** ⭐ **IMPLEMENTED**

### Naming Pattern:
- **Comprehensive Tools**: `action_entity_enriched` (e.g., `get_appointments_enriched`)
- **Basic Tools**: `action_entity_basic` (e.g., `get_appointments_basic`)

### Description Strategy:
- **Comprehensive**: Start with 🌟 **RECOMMENDED** and explain benefits
- **Basic**: Start with ⚠️ warning and suggest the comprehensive alternative

### Example:
```python
@mcp.tool()
async def get_appointments_enriched(...):
    """
    🌟 RECOMMENDED: Get appointments with comprehensive details including patient names, doctor profiles, and clinic information.
    
    This is the preferred tool for getting appointment information as it provides complete context
    without requiring additional API calls. Use this instead of get_appointments_basic unless you
    specifically need only basic appointment data.
    """

@mcp.tool()
async def get_appointments_basic(...):
    """
    Get basic appointments data (IDs only). 
    
    ⚠️  Consider using get_appointments_enriched instead for complete information.
    Only use this if you specifically need raw appointment data without patient/doctor/clinic details.
    """
```

## **2. Tool Ordering Strategy**

Register comprehensive tools BEFORE basic tools in the MCP so they appear first in tool lists:

```python
def register_appointment_tools(mcp: FastMCP) -> None:
    # Comprehensive tools first
    mcp.tool()(get_appointments_enriched)
    mcp.tool()(get_appointment_details_enriched)
    mcp.tool()(get_patient_appointments_enriched)
    
    # Basic tools later
    mcp.tool()(get_appointments_basic)
    mcp.tool()(get_appointment_details_basic)
    mcp.tool()(get_patient_appointments_basic)
```

## **3. Tool Categorization Strategy**

### Option A: Separate Tool Categories
```python
def register_appointment_tools(mcp: FastMCP) -> None:
    # === COMPREHENSIVE TOOLS (RECOMMENDED) ===
    register_comprehensive_appointment_tools(mcp)
    
    # === BASIC TOOLS (ADVANCED USE ONLY) ===
    register_basic_appointment_tools(mcp)
```

### Option B: Tool Tags/Metadata
```python
@mcp.tool(
    name="get_appointments_enriched",
    category="comprehensive",
    priority="high",
    tags=["recommended", "enriched", "complete"]
)
```

## **4. Smart Default Parameters Strategy**

Make comprehensive behavior the default with opt-out parameters:

```python
@mcp.tool()
async def get_appointments(
    doctor_id: Optional[str] = None,
    clinic_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page_no: int = 0,
    include_enrichment: bool = True,  # Default to comprehensive
    enrichment_level: str = "full"   # "full", "partial", "none"
) -> Dict[str, Any]:
    """
    Get appointments with configurable enrichment level.
    
    Args:
        include_enrichment: Whether to include patient/doctor/clinic details (default: True)
        enrichment_level: Level of enrichment - "full" (all details), "partial" (names only), "none" (IDs only)
    """
    if not include_enrichment or enrichment_level == "none":
        return await get_basic_appointments(...)
    elif enrichment_level == "partial":
        return await get_partially_enriched_appointments(...)
    else:  # full enrichment
        return await get_fully_enriched_appointments(...)
```

## **5. Tool Aliasing Strategy**

Provide multiple names for the same comprehensive tool:

```python
# Primary comprehensive tool
@mcp.tool(name="get_comprehensive_patient_profile")
async def get_comprehensive_patient_profile(...):
    """🌟 RECOMMENDED: Complete patient profile with appointment history"""

# Alias that sounds like the basic version but calls comprehensive
@mcp.tool(name="get_patient_details")
async def get_patient_details_alias(...):
    """Get patient details (comprehensive by default)"""
    return await get_comprehensive_patient_profile(...)

# Explicit basic version for advanced users
@mcp.tool(name="get_patient_details_basic_only")
async def get_patient_details_basic(...):
    """⚠️ ADVANCED: Get only basic patient data without enrichment"""
```

## **6. Progressive Enhancement Strategy**

Start with comprehensive tools and provide "lite" versions:

```python
@mcp.tool()
async def get_patient_profile(
    patient_id: str,
    include_appointments: bool = True,
    include_prescriptions: bool = True,
    include_vitals: bool = True,
    appointment_limit: int = 10
) -> Dict[str, Any]:
    """
    🌟 RECOMMENDED: Get complete patient profile with all related data.
    
    Disable specific sections if you need faster responses:
    - Set include_appointments=False to skip appointment history
    - Set include_prescriptions=False to skip prescription history
    - Set appointment_limit=0 to get profile only
    """
```

## **7. MCP Configuration Strategy**

### Option A: Environment-based defaults
```python
# Set via environment variable
COMPREHENSIVE_TOOLS_DEFAULT = os.getenv("EKA_MCP_COMPREHENSIVE_DEFAULT", "true")

def should_use_comprehensive() -> bool:
    return COMPREHENSIVE_TOOLS_DEFAULT.lower() == "true"
```

### Option B: MCP-level configuration
```python
class EkaMCPConfig:
    def __init__(self):
        self.default_to_comprehensive = True
        self.show_basic_tools = True
        self.comprehensive_timeout = 30  # seconds
```

## **8. Documentation Strategy**

### Tool Documentation Hierarchy:
1. **Comprehensive tools**: Detailed examples, use cases
2. **Basic tools**: Minimal documentation with redirect to comprehensive

### README Examples:
```markdown
## Quick Start - Recommended Tools

For most use cases, use these comprehensive tools:
- `get_appointments_enriched()` - Complete appointment data
- `get_comprehensive_patient_profile()` - Full patient context
- `get_comprehensive_doctor_profile()` - Complete doctor information

## Advanced Usage - Basic Tools

For specialized use cases where you need only IDs:
- `get_appointments_basic()` - Raw appointment data
- `get_patient_details_basic()` - Basic patient info only
```

## **9. Performance-based Selection**

Provide performance hints in descriptions:

```python
@mcp.tool()
async def get_appointments_enriched(...):
    """
    🌟 RECOMMENDED: Get comprehensive appointment data.
    
    Performance: ~200ms average response time
    API Calls: Optimized with caching (1-3 calls total)
    Use Case: Complete appointment context for LLM processing
    """

@mcp.tool()
async def get_appointments_basic(...):
    """
    Basic appointment data (IDs only).
    
    Performance: ~50ms average response time  
    API Calls: Single call
    Use Case: When you only need to verify appointment existence
    ⚠️ Most use cases benefit from get_appointments_enriched instead
    """
```

## **Implementation Status**

✅ **Strategy 1**: Tool naming convention with `_enriched` and `_basic` suffixes
✅ **Strategy 1**: Comprehensive descriptions with 🌟 RECOMMENDED and ⚠️ warnings
🔄 **Strategy 2**: Tool ordering (needs implementation in registration)
⏳ **Strategy 4**: Smart defaults (future enhancement)
⏳ **Strategy 6**: Progressive enhancement (future enhancement)

## **Recommended Implementation Order**

1. ✅ **Complete naming convention** (partially done)
2. **Apply to all tool categories** (patient, doctor, prescription tools)
3. **Implement tool ordering** in registration
4. **Add performance hints** to descriptions
5. **Consider smart defaults** for future versions