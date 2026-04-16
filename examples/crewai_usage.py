#!/usr/bin/env python3
"""
Eka.care MCP SDK - CrewAI Integration Example

This example demonstrates how to integrate the Eka.care MCP SDK with CrewAI
for building AI-powered healthcare workflow automation. It shows how to create
specialized agents that can interact with Eka.care APIs.

Setup:
1. pip install crewai
2. Copy .env.example to .env and configure your credentials  
3. pip install -e .
4. python examples/crewai_usage.py

Dependencies:
- crewai
- eka-mcp-sdk
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
except ImportError:
    print("❌ CrewAI not installed. Please install it with: pip install crewai")
    exit(1)

from eka_mcp_sdk.clients.eka_emr_client import EkaEMRClient
from eka_mcp_sdk.auth.models import EkaAPIError
from eka_mcp_sdk.config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EkaCareBaseTool(BaseTool):
    """Base tool class for Eka.care API integrations with CrewAI."""
    client: Optional[EkaEMRClient] = None
    
    def __init__(self):
        super().__init__()
        self.client = EkaEMRClient()
    
    async def _execute_async(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute the async operation. To be implemented by subclasses."""
        raise NotImplementedError
    
    def _run(self, *args, **kwargs) -> str:
        """Synchronous wrapper for async operations."""
        try:
            # Run the async operation in the current event loop
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new task
                task = asyncio.create_task(self._execute_async(*args, **kwargs))
                # Note: This is a simplified approach. In production, you might want
                # to use asyncio.run_coroutine_threadsafe or similar
                result = asyncio.run(self._execute_async(*args, **kwargs))
            else:
                result = asyncio.run(self._execute_async(*args, **kwargs))
            
            return str(result) if result else "Operation completed"
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return f"Error: {str(e)}"


class PatientSearchTool(EkaCareBaseTool):
    """Tool for searching patients in Eka.care system."""
    
    name: str = "patient_search"
    description: str = "Search for patients by name, mobile number, or other identifiers"
    
    async def _execute_async(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search for patients."""
        try:
            result = await self.client.search_patients(prefix=query, limit=limit)
            return result
        except EkaAPIError as e:
            return {"success": False, "error": str(e)}


class AppointmentBookingTool(EkaCareBaseTool):
    """Tool for booking appointments."""
    
    name: str = "book_appointment"
    description: str = "Book appointments for patients with doctors"
    
    async def _execute_async(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Book an appointment."""
        try:
            result = await self.client.book_appointment(appointment_data)
            return result
        except EkaAPIError as e:
            return {"success": False, "error": str(e)}


class AppointmentSlotsTool(EkaCareBaseTool):
    """Tool for checking available appointment slots."""
    
    name: str = "check_appointment_slots"
    description: str = "Check available appointment slots for doctors"
    
    async def _execute_async(self, doctor_id: str, clinic_id: str, date: str) -> Dict[str, Any]:
        """Get available appointment slots."""
        try:
            result = await self.client.get_appointment_slots(doctor_id, clinic_id, date)
            return result
        except EkaAPIError as e:
            return {"success": False, "error": str(e)}


class DoctorProfileTool(EkaCareBaseTool):
    """Tool for getting doctor information."""
    
    name: str = "get_doctor_info"
    description: str = "Get detailed information about doctors and their specializations"
    
    async def _execute_async(self, doctor_id: str = None) -> Dict[str, Any]:
        """Get doctor information."""
        try:
            if doctor_id:
                result = await self.client.get_doctor_profile(doctor_id)
            else:
                result = await self.client.get_business_entities()
            return result
        except EkaAPIError as e:
            return {"success": False, "error": str(e)}


def create_healthcare_agents() -> List[Agent]:
    """Create specialized healthcare agents with Eka.care tools."""
    
    # Initialize tools
    patient_search = PatientSearchTool()
    appointment_booking = AppointmentBookingTool()
    appointment_slots = AppointmentSlotsTool()
    doctor_profile = DoctorProfileTool()
    
    # Patient Management Agent
    patient_agent = Agent(
        role='Patient Care Coordinator',
        goal='Efficiently manage patient information, search records, and coordinate patient care',
        backstory="""You are a skilled patient care coordinator with deep knowledge of healthcare 
        systems and patient management. You excel at finding patient records, managing patient 
        information, and ensuring accurate patient data across the healthcare system.""",
        tools=[patient_search],
        verbose=True,
        allow_delegation=False
    )
    
    # Appointment Scheduling Agent  
    scheduler_agent = Agent(
        role='Appointment Scheduler',
        goal='Manage appointment scheduling, check availability, and coordinate doctor-patient meetings',
        backstory="""You are an experienced appointment scheduler who understands the complexities 
        of healthcare scheduling. You are skilled at finding optimal appointment times, managing 
        doctor availability, and ensuring efficient scheduling for both patients and healthcare providers.""",
        tools=[appointment_slots, appointment_booking],
        verbose=True,
        allow_delegation=False
    )
    
    # Healthcare Information Agent
    info_agent = Agent(
        role='Healthcare Information Specialist',
        goal='Provide comprehensive information about doctors, clinics, and healthcare services',
        backstory="""You are a healthcare information specialist with extensive knowledge about 
        medical practitioners, their specializations, and healthcare facilities. You help patients 
        and staff understand available healthcare resources and make informed decisions.""",
        tools=[doctor_profile],
        verbose=True,
        allow_delegation=False
    )
    
    return [patient_agent, scheduler_agent, info_agent]


def create_healthcare_tasks(agents: List[Agent]) -> List[Task]:
    """Create healthcare workflow tasks."""
    
    patient_agent, scheduler_agent, info_agent = agents
    
    # Task 1: Patient Information Gathering
    patient_task = Task(
        description="""Search for patient records to gather comprehensive information about patients 
        who need appointments. Focus on finding patients with mobile numbers starting with '+91' 
        and compile their basic information for scheduling purposes.""",
        agent=patient_agent,
        expected_output="A summary of found patients with their key information"
    )
    
    # Task 2: Healthcare Provider Information
    provider_task = Task(
        description="""Gather information about available doctors and healthcare providers. 
        Compile details about their specializations, availability, and associated clinics to 
        help with appointment scheduling decisions.""",
        agent=info_agent,
        expected_output="A comprehensive overview of available healthcare providers"
    )
    
    # Task 3: Appointment Coordination
    scheduling_task = Task(
        description="""Based on the patient and provider information gathered, coordinate potential 
        appointment scheduling by checking available slots and preparing appointment recommendations. 
        Consider patient needs and doctor availability.""",
        agent=scheduler_agent,
        expected_output="Appointment scheduling recommendations with available time slots",
        context=[patient_task, provider_task]  # Depends on previous tasks
    )
    
    return [patient_task, provider_task, scheduling_task]


async def demo_healthcare_workflow():
    """Demonstrate a complete healthcare workflow using CrewAI and Eka.care."""
    
    print("🏥 Healthcare Workflow Demo with CrewAI + Eka.care")
    print("="*60)
    
    # Verify configuration
    if not settings.client_id:
        print("❌ Missing EKA_CLIENT_ID in configuration")
        return
    
    print(f"✅ Using Eka.care API: {settings.api_base_url}")
    print(f"✅ Authentication configured: {settings.client_id}")
    
    # Create agents and tasks
    print("\n🤖 Creating specialized healthcare agents...")
    agents = create_healthcare_agents()
    
    print("📋 Setting up healthcare workflow tasks...")
    tasks = create_healthcare_tasks(agents)
    
    # Create and run crew
    print("\n🚀 Starting healthcare workflow execution...")
    
    healthcare_crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )
    
    try:
        # Execute the workflow
        result = healthcare_crew.kickoff()
        
        print("\n" + "="*60)
        print("✨ Healthcare Workflow Completed!")
        print("="*60)
        print(result)
        
    except Exception as e:
        print(f"\n❌ Workflow execution failed: {str(e)}")
        logger.error(f"CrewAI workflow error: {str(e)}")


async def demo_individual_tools():
    """Demonstrate individual Eka.care tools with CrewAI."""
    
    print("\n🔧 Testing Individual Eka.care Tools")
    print("="*40)
    
    # Test patient search tool
    print("\n👥 Testing Patient Search Tool...")
    patient_tool = PatientSearchTool()
    try:
        search_result = patient_tool._run(query="+91", limit=3)
        print(f"Patient search result: {search_result[:200]}...")
    except Exception as e:
        print(f"❌ Patient search failed: {str(e)}")
    
    # Test doctor profile tool  
    print("\n👨‍⚕️ Testing Doctor Profile Tool...")
    doctor_tool = DoctorProfileTool()
    try:
        doctor_result = doctor_tool._run()
        print(f"Doctor info result: {doctor_result[:200]}...")
    except Exception as e:
        print(f"❌ Doctor info failed: {str(e)}")


def print_setup_instructions():
    """Print setup instructions for the demo."""
    
    print("""
🏥 Eka.care + CrewAI Integration Demo

This demo shows how to integrate Eka.care healthcare APIs with CrewAI for 
building intelligent healthcare workflow automation.

## Setup Required:

1. **Install Dependencies**
   ```bash
   pip install crewai
   pip install -e .
   ```

2. **Configure Eka.care Credentials**
   Update your .env file with:
   ```env
   EKA_CLIENT_ID=your_client_id
   EKA_CLIENT_SECRET=your_client_secret
   EKA_API_KEY=your_api_key  # Optional
   ```

3. **Run the Demo**
   ```bash
   python examples/crewai_usage.py
   ```

## What this demo demonstrates:

✅ **Multi-Agent Healthcare Workflow**
  - Patient Care Coordinator (patient search & management)
  - Appointment Scheduler (booking & availability)  
  - Healthcare Information Specialist (doctor & clinic info)

✅ **Eka.care API Integration**
  - Patient search and management
  - Appointment scheduling and slots
  - Doctor and clinic information
  - Error handling and logging

✅ **CrewAI Features**
  - Sequential task processing
  - Agent collaboration and context sharing
  - Tool integration with healthcare APIs
  - Workflow orchestration

## Use Cases:

🎯 **Automated Patient Intake**
  - Search existing patient records
  - Gather patient information
  - Prepare for appointment booking

🎯 **Intelligent Scheduling**  
  - Check doctor availability
  - Match patient needs with provider specializations
  - Optimize appointment scheduling

🎯 **Healthcare Coordination**
  - Multi-step patient care workflows
  - Provider network management
  - Appointment and care coordination

Ready to start? Make sure your credentials are configured and run the demo!
""")


async def main():
    """Main demo function."""
    
    print_setup_instructions()
    
    # Check if CrewAI is available
    try:
        import crewai
        print("✅ CrewAI is available")
    except ImportError:
        print("❌ CrewAI not found. Please install: pip install crewai")
        return
    
    # Check configuration
    if not settings.client_id:
        print("⚠️  EKA_CLIENT_ID not configured. Please update your .env file.")
        return
    
    # Run individual tool demos first
    await demo_individual_tools()
    
    # Run full workflow demo
    await demo_healthcare_workflow()
    
    print("\n" + "="*60)
    print("🎉 CrewAI + Eka.care Integration Demo Completed!")
    print("💡 Tip: Customize agents and tasks for your specific healthcare workflows")
    print("📖 Learn more: https://docs.crewai.com/")


if __name__ == "__main__":
    asyncio.run(main())