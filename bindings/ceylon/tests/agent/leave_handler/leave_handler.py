#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
from datetime import date, timedelta
from loguru import logger

from agent.leave_handler.agents import *


async def main():
    # Initialize the leave manager
    leave_manager = LeaveManager()
    admin_details = leave_manager.details()

    # Create sample employee data
    employee1 = EmployeeData(
        employee_id="EMP001",
        department="Engineering",
        role="Software Engineer",
        leave_balance={
            LeaveType.VACATION: 15,
            LeaveType.SICK: 10,
            LeaveType.PERSONAL: 5
        },
        manager_id="MGR001"
    )

    employee2 = EmployeeData(
        employee_id="EMP002",
        department="Engineering",
        role="Senior Engineer",
        leave_balance={
            LeaveType.VACATION: 20,
            LeaveType.SICK: 10,
            LeaveType.PERSONAL: 5
        },
        manager_id="MGR001"
    )

    # Initialize agents
    employee_agent1 = EmployeeAgent(
        employee_data=employee1,
        admin_peer=admin_details.id
    )

    employee_agent2 = EmployeeAgent(
        employee_data=employee2,
        admin_peer=admin_details.id
    )

    team_calendar = TeamCalendarAgent(
        admin_peer=admin_details.id
    )

    await leave_manager.arun_admin(b"", [employee_agent1, employee_agent2, team_calendar])


if __name__ == '__main__':
    asyncio.run(main())
