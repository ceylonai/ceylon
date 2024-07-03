from expert_ceylon import *


class Task(Fact):
    """Information about a task"""
    pass


class Agent(Fact):
    """Information about an agent"""
    pass


class TaskManagement(KnowledgeEngine):
    def __init__(self, dependencies):
        super().__init__()
        self.dependencies = dependencies
        self.create_dynamic_rules()

    def create_dynamic_rules(self):
        for task, deps in self.dependencies.items():
            self.add_rule(task, deps)

    def add_rule(self, task, dependencies):
        def rule_method(self):
            all_deps_completed = all(
                self.facts.get(Task(name=dep)).get('status') == 'completed'
                for dep in dependencies
            )
            if all_deps_completed:
                print(f"{task} is being handled.")
                self.modify(self.facts[Task(name=task)], status='completed')

        rule_method.__name__ = f"handle_{task}"
        setattr(self, rule_method.__name__, Rule(Task(name=task, status='pending'))(rule_method))


def add_task(engine, name, status, required_ability, dependency=None):
    engine.declare(Task(name=name, status=status))


def add_agent(engine, name, ability):
    engine.declare(Agent(name=name, ability=ability))


def main():
    dependencies = {
        "name_chooser": [],
        "researcher": [],
        "writer": ["researcher"],
        "editor": ["writer"],
        "publisher": ["editor", "name_chooser"]
    }

    engine = TaskManagement(dependencies)
    engine.reset()

    # Initial facts
    add_task(engine, 'name_chooser', 'pending', 'choose_name')
    add_task(engine, 'researcher', 'pending', 'research')
    add_task(engine, 'writer', 'pending', 'write')
    add_task(engine, 'editor', 'pending', 'edit')
    add_task(engine, 'publisher', 'pending', 'publish')

    add_agent(engine, 'name_chooser', 'choose_name')
    add_agent(engine, 'researcher', 'research')
    add_agent(engine, 'writer', 'write')
    add_agent(engine, 'editor', 'edit')
    add_agent(engine, 'publisher', 'publish')

    # Running the engine
    engine.run()

    # Adding new tasks and agents dynamically
    add_task(engine, 'additional_task', 'pending', 'additional_ability', 'publish')
    add_agent(engine, 'additional_agent', 'additional_ability')

    # Running the engine again to process new tasks
    engine.run()


if __name__ == "__main__":
    main()
