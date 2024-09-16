from statemachine import StateMachine, State


class TrafficLightMachine(StateMachine):
    "A traffic light machine"
    green = State(initial=True)
    yellow = State()
    red = State()

    cycle = (
            green.to(yellow)
            | yellow.to(red)
            | red.to(green)
    )

    def before_cycle(self, event: str, source: State, target: State, message: str = ""):
        message = ". " + message if message else ""
        return f"Running {event} from {source.id} to {target.id}{message}"

    def on_enter_red(self):
        print("Don't move.")

    def on_exit_red(self):
        print("Go ahead!")
