#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import List, Dict, Optional


class LeaveStatus(Enum):
    PENDING = "pending"
    SUGGESTED = "suggested"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LeaveType(Enum):
    VACATION = "vacation"
    SICK = "sick"
    PERSONAL = "personal"
    OTHER = "other"


@dataclass
class TimeRange:
    start_date: date
    end_date: date

    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


@dataclass
class LeaveRequest:
    employee_id: str
    leave_type: LeaveType
    preferred_range: TimeRange
    flexibility_days: int  # How many days flexible before/after preferred dates
    minimum_days: int
    maximum_days: int
    special_preferences: Optional[str] = None


@dataclass
class LeaveSuggestion:
    request_id: str
    suggested_range: TimeRange
    optimization_score: float
    reason: str


@dataclass
class LeaveResponse:
    request_id: str
    status: LeaveStatus
    message: Optional[str] = None
    suggestions: Optional[List[LeaveSuggestion]] = None


@dataclass
class TeamCalendarEntry:
    date: date
    employee_id: str
    status: str  # "present", "leave", "holiday"
    note: Optional[str] = None


@dataclass
class EmployeeData:
    employee_id: str
    department: str
    role: str
    leave_balance: Dict[LeaveType, int]
    manager_id: str


class CalendarQuery:
    start_date: date
    end_date: date
    department: Optional[str] = None


class DepartmentCoverage:
    department: str
    date: date
    total_employees: int
    present_employees: int
    minimum_required: int


# Message types for agent communication
@dataclass
class RequestAvailabilityCheck:
    leave_request: LeaveRequest
    calendar_query: CalendarQuery


@dataclass
class AvailabilityResponse:
    request_id: str
    available_ranges: List[TimeRange]
    coverage_data: List[DepartmentCoverage]


@dataclass
class SuggestionRequest:
    leave_request: LeaveRequest
    available_ranges: List[TimeRange]
    coverage_data: List[DepartmentCoverage]


@dataclass
class Notification:
    recipient_id: str
    message: str
    notification_type: str
    timestamp: datetime
    related_request_id: Optional[str] = None
