import asyncio

from statemachine import StateMachine, State


class AsyncStateMachine(StateMachine):
    initial = State('Initial', initial=True)
    final = State('Final', final=True)

    keep = initial.to.itself(internal=True)
    advance = initial.to(final)

    async def on_advance(self):
        return 42


async def run_sm():
    sm = AsyncStateMachine()
    result = await sm.advance()
    print(f"Result is {result}")
    print(sm.current_state)


if __name__ == '__main__':
    asyncio.run(run_sm())
