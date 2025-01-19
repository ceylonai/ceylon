#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import pickle
from datetime import timedelta

from loguru import logger

from agent.leave_handler.data import *
from ceylon import AgentDetail
from ceylon.base.agents import Admin, Worker


class LeaveManager(Admin):
    """Central administrator for the leave management system"""

    def __init__(self, name="leave_manager", port=8888):
        super().__init__(name=name, port=port)
        self.employee_data: Dict[str, EmployeeData] = {}
        self.pending_requests: Dict[str, LeaveRequest] = {}
        self.request_suggestions: Dict[str, List[LeaveSuggestion]] = {}

    async def run(self, inputs: bytes):
        logger.info(f"Leave Manager started - {self.details().name}")
        while True:
            await asyncio.sleep(1)

    async def on_agent_connected(self, topic: str, agent_id: AgentDetail):
        logger.info(f"Agent connected: {agent_id}")
        welcome_msg = {
            "type": "welcome",
            "message": f"Welcome {agent_id}"
        }
        await self.send_direct_data(agent_id.id, pickle.dumps(welcome_msg))

    async def on_message(self, agent_id: str, data: bytes, time: int):
        message = pickle.loads(data)

        if isinstance(message, LeaveRequest):
            await self.handle_leave_request(agent_id, message)
        elif isinstance(message, AvailabilityResponse):
            await self.handle_availability_response(message)
        elif isinstance(message, LeaveSuggestion):
            await self.handle_suggestion(message)

    async def handle_leave_request(self, employee_id: str, request: LeaveRequest):
        request_id = f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}_{employee_id}"
        self.pending_requests[request_id] = request

        # Query calendar for availability
        calendar_query = CalendarQuery(
            start_date=request.preferred_range.start_date - timedelta(days=request.flexibility_days),
            end_date=request.preferred_range.end_date + timedelta(days=request.flexibility_days),
            department=self.employee_data[employee_id].department
        )

        availability_check = RequestAvailabilityCheck(request, calendar_query)
        await self.broadcast(pickle.dumps(availability_check))

    async def handle_availability_response(self, response: AvailabilityResponse):
        request = self.pending_requests.get(response.request_id)
        if not request:
            return

        suggestion_request = SuggestionRequest(
            leave_request=request,
            available_ranges=response.available_ranges,
            coverage_data=response.coverage_data
        )
        await self.broadcast(pickle.dumps(suggestion_request))


class EmployeeAgent(Worker):
    """Represents an employee in the system"""

    def __init__(self, employee_data: EmployeeData, workspace_id="leave_management",
                 admin_peer="", admin_port=8888):
        super().__init__(
            name=employee_data.employee_id,
            workspace_id=workspace_id,
            admin_peer=admin_peer,
            admin_port=admin_port
        )
        self.employee_data = employee_data
        self.pending_requests: Dict[str, LeaveRequest] = {}

    async def submit_leave_request(self, request: LeaveRequest):
        self.pending_requests[request.employee_id] = request
        await self.broadcast(pickle.dumps(request))

    async def on_message(self, agent_id: str, data: bytes, time: int):
        message = pickle.loads(data)

        if isinstance(message, LeaveResponse):
            await self.handle_leave_response(message)
        elif isinstance(message, Notification):
            await self.handle_notification(message)

    async def handle_leave_response(self, response: LeaveResponse):
        if response.status == LeaveStatus.SUGGESTED:
            logger.info(f"Received suggestions for request {response.request_id}")
            # Here you would typically notify the UI about available suggestions

    async def handle_notification(self, notification: Notification):
        logger.info(f"Received notification: {notification.message}")


class TeamCalendarAgent(Worker):
    """Manages team calendar and availability checking"""

    def __init__(self, workspace_id="leave_management", admin_peer="", admin_port=8888):
        super().__init__(
            name="team_calendar",
            workspace_id=workspace_id,
            admin_peer=admin_peer,
            admin_port=admin_port
        )
        self.calendar_entries: Dict[date, List[TeamCalendarEntry]] = {}
        self.department_rules: Dict[str, int] = {}  # department -> minimum required employees

    async def on_message(self, agent_id: str, data: bytes, time: int):
        message = pickle.loads(data)

        if isinstance(message, RequestAvailabilityCheck):
            await self.check_availability(message)

    async def check_availability(self, request: RequestAvailabilityCheck):
        available_ranges = []
        coverage_data = []

        current_date = request.calendar_query.start_date
        while current_date <= request.calendar_query.end_date:
            coverage = self.calculate_coverage(
                current_date,
                request.calendar_query.department
            )
            coverage_data.append(coverage)

            # Check if adding this leave would maintain minimum coverage
            if self.is_date_available(current_date, coverage):
                available_ranges.append(TimeRange(current_date, current_date))

            current_date += timedelta(days=1)

        # Merge consecutive available dates into ranges
        merged_ranges = self.merge_available_ranges(available_ranges)

        response = AvailabilityResponse(
            request_id=id(request),
            available_ranges=merged_ranges,
            coverage_data=coverage_data
        )
        await self.broadcast(pickle.dumps(response))

    def calculate_coverage(self, date: date, department: str) -> DepartmentCoverage:
        entries = self.calendar_entries.get(date, [])
        total = len([e for e in entries if e.status != "holiday"])
        present = len([e for e in entries if e.status == "present"])
        minimum = self.department_rules.get(department, 1)

        return DepartmentCoverage(
            department=department,
            date=date,
            total_employees=total,
            present_employees=present,
            minimum_required=minimum
        )

    def is_date_available(self, date: date, coverage: DepartmentCoverage) -> bool:
        return coverage.present_employees > coverage.minimum_required

    @staticmethod
    def merge_available_ranges(ranges: List[TimeRange]) -> List[TimeRange]:
        if not ranges:
            return []

        merged = []
        current_range = ranges[0]

        for next_range in ranges[1:]:
            if (current_range.end_date + timedelta(days=1)) >= next_range.start_date:
                current_range = TimeRange(
                    current_range.start_date,
                    max(current_range.end_date, next_range.end_date)
                )
            else:
                merged.append(current_range)
                current_range = next_range

        merged.append(current_range)
        return merged


class SchedulingSuggestionAgent(Worker):
    """Generates and ranks leave date suggestions"""

    def __init__(self, workspace_id="leave_management", admin_peer="", admin_port=8888):
        super().__init__(
            name="scheduling_suggestion",
            workspace_id=workspace_id,
            admin_peer=admin_peer,
            admin_port=admin_port
        )

    async def on_message(self, agent_id: str, data: bytes, time: int):
        message = pickle.loads(data)

        if isinstance(message, SuggestionRequest):
            await self.generate_suggestions(message)

    async def generate_suggestions(self, request: SuggestionRequest):
        suggestions = []

        for available_range in request.available_ranges:
            score = self.calculate_optimization_score(
                available_range,
                request.leave_request,
                request.coverage_data
            )

            suggestion = LeaveSuggestion(
                request_id=id(request),
                suggested_range=available_range,
                optimization_score=score,
                reason=self.generate_suggestion_reason(
                    available_range,
                    score,
                    request.coverage_data
                )
            )
            suggestions.append(suggestion)

        # Sort suggestions by score
        suggestions.sort(key=lambda x: x.optimization_score, reverse=True)

        # Send top suggestions
        for suggestion in suggestions[:3]:
            await self.broadcast(pickle.dumps(suggestion))

    def calculate_optimization_score(
            self,
            range: TimeRange,
            request: LeaveRequest,
            coverage_data: List[DepartmentCoverage]
    ) -> float:
        # Implement scoring logic based on:
        # 1. Proximity to preferred dates
        # 2. Team coverage levels
        # 3. Holiday adjacency
        # 4. Historical patterns
        # Returns a score between 0 and 1
        return 0.5  # Placeholder implementation

    def generate_suggestion_reason(
            self,
            range: TimeRange,
            score: float,
            coverage_data: List[DepartmentCoverage]
    ) -> str:
        # Generate human-readable explanation for the suggestion
        return f"Suggested dates have good team coverage and align with preferences"
