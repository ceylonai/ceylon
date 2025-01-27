use std::collections::{HashMap, HashSet};

// Core task states that represent the lifecycle
#[derive(Debug, Clone, PartialEq)]
pub enum TaskState {
    Ready,
    Running,
    Complete,
    Failed(String),
    Skipped,
}

// Core workflow states
#[derive(Debug, Clone, PartialEq)]
pub enum WorkflowState {
    New,
    Running,
    Complete,
    Failed(String),
}

// Core task definition that others can extend
pub trait Task {
    fn id(&self) -> &str;
    fn run(&mut self) -> Result<(), String>;
    fn state(&self) -> &TaskState;
    fn set_state(&mut self, state: TaskState);
    fn dependencies(&self) -> &[String] { &[] }
}

// Core workflow engine that manages task execution
pub struct Workflow {
    id: String,
    state: WorkflowState,
    tasks: HashMap<String, Box<dyn Task>>,
    completed: HashSet<String>,
}

impl Workflow {
    pub fn new(id: String) -> Self {
        Workflow {
            id,
            state: WorkflowState::New,
            tasks: HashMap::new(),
            completed: HashSet::new(),
        }
    }

    pub fn add_task(&mut self, task: Box<dyn Task>) -> Result<(), String> {
        let task_id = task.id().to_string();

        // Add the task
        self.tasks.insert(task_id.clone(), task);

        // Create temporary dependency map including the new task
        let dep_map: HashMap<String, Vec<String>> = self.tasks.iter()
            .map(|(id, task)| (id.clone(), task.dependencies().to_vec()))
            .collect();

        // Check for cycles with all current tasks
        for start_task in dep_map.keys() {
            let mut visited = HashSet::new();
            let mut stack = HashSet::new();

            if self.has_cycle_from_node(start_task, &dep_map, &mut visited, &mut stack) {
                // Remove the task if it creates a cycle
                self.tasks.remove(&task_id);
                return Err(format!("Adding task {} would create a dependency cycle", task_id));
            }
        }

        Ok(())
    }

    // Validates all dependencies exist and there are no cycles
    pub fn validate(&self) -> Result<(), String> {
        // Check all dependencies exist
        for (id, task) in &self.tasks {
            for dep in task.dependencies() {
                if !self.tasks.contains_key(dep) {
                    return Err(format!("Task {} depends on missing task {}", id, dep));
                }
            }
        }

        // Check for cycles
        if self.has_cycles() {
            return Err("Workflow contains dependency cycles".to_string());
        }

        Ok(())
    }

    fn has_cycles(&self) -> bool {
        let dep_map: HashMap<String, Vec<String>> = self.tasks.iter()
            .map(|(id, task)| (id.clone(), task.dependencies().to_vec()))
            .collect();

        // Check each task for cycles
        for start_task in dep_map.keys() {
            let mut visited = HashSet::new();
            let mut stack = HashSet::new();

            if self.has_cycle_from_node(start_task, &dep_map, &mut visited, &mut stack) {
                return true;
            }
        }
        false
    }

    fn has_cycle_from_node(
        &self,
        node: &str,
        dep_map: &HashMap<String, Vec<String>>,
        visited: &mut HashSet<String>,
        stack: &mut HashSet<String>
    ) -> bool {
        if stack.contains(node) {
            return true;
        }
        if visited.contains(node) {
            return false;
        }

        visited.insert(node.to_string());
        stack.insert(node.to_string());

        if let Some(deps) = dep_map.get(node) {
            for dep in deps {
                if self.has_cycle_from_node(dep, dep_map, visited, stack) {
                    return true;
                }
            }
        }

        stack.remove(node);
        false
    }

    fn would_create_cycle(&self, new_task: &str, new_deps: &[String]) -> bool {
        // Map to track task -> dependencies for existing tasks plus the new task
        let mut dep_map: HashMap<String, Vec<String>> = self.tasks.iter()
            .map(|(id, task)| (id.clone(), task.dependencies().to_vec()))
            .collect();

        // Add the new task's dependencies
        dep_map.insert(new_task.to_string(), new_deps.to_vec());

        // For each task (including the new one), check if it can reach itself
        for start_task in dep_map.keys() {
            let mut visited = HashSet::new();
            let mut stack = vec![start_task.clone()];

            while let Some(current) = stack.pop() {
                if !visited.insert(current.clone()) {
                    // If we've seen this task before and it's our start task,
                    // we've found a cycle
                    if current == *start_task {
                        return true;
                    }
                    continue;
                }

                // Add all dependencies of current task to stack
                if let Some(deps) = dep_map.get(&current) {
                    stack.extend(deps.iter().cloned());
                }
            }
        }
        false
    }

    pub fn run(&mut self) -> Result<(), String> {
        // Validate dependencies before running
        self.validate()?;

        self.state = WorkflowState::Running;

        // Keep running until all tasks are processed or failure
        while !self.tasks.is_empty() {
            let available = self.get_available_tasks();

            if available.is_empty() && !self.tasks.is_empty() {
                self.state = WorkflowState::Failed("Deadlock detected".to_string());
                return Err("Workflow deadlocked - circular dependency or all tasks blocked".to_string());
            }

            // Run all available tasks
            for task_id in available {
                if let Some(task) = self.tasks.get_mut(&task_id) {
                    task.set_state(TaskState::Running);

                    match task.run() {
                        Ok(()) => {
                            task.set_state(TaskState::Complete);
                            self.completed.insert(task_id.clone());
                        }
                        Err(e) => {
                            task.set_state(TaskState::Failed(e.clone()));
                            self.state = WorkflowState::Failed(format!("Task {} failed: {}", task_id, e));
                            return Err(format!("Workflow failed at task {}: {}", task_id, e));
                        }
                    }
                }
            }

            // Remove completed tasks
            self.tasks.retain(|id, _| !self.completed.contains(id));
        }

        self.state = WorkflowState::Complete;
        Ok(())
    }

    fn get_available_tasks(&self) -> Vec<String> {
        self.tasks.iter()
            .filter(|(id, task)| {
                matches!(task.state(), TaskState::Ready) &&
                    task.dependencies().iter().all(|dep| self.completed.contains(dep))
            })
            .map(|(id, _)| id.clone())
            .collect()
    }

    pub fn state(&self) -> &WorkflowState {
        &self.state
    }
}

// Example of how to extend the system with a custom task
pub struct FileProcessingTask {
    task_id: String,
    state: TaskState,
    filepath: String,
    deps: Vec<String>,
}

impl FileProcessingTask {
    pub fn new(id: String, filepath: String, dependencies: Vec<String>) -> Self {
        FileProcessingTask {
            task_id: id,
            state: TaskState::Ready,
            filepath,
            deps: dependencies,
        }
    }
}

impl Task for FileProcessingTask {
    fn id(&self) -> &str {
        &self.task_id
    }

    fn run(&mut self) -> Result<(), String> {
        // Example implementation
        println!("Processing file: {}", self.filepath);
        // Add actual file processing logic here
        Ok(())
    }

    fn state(&self) -> &TaskState {
        &self.state
    }

    fn set_state(&mut self, state: TaskState) {
        self.state = state;
    }

    fn dependencies(&self) -> &[String] {
        &self.deps
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestTask {
        id: String,
        state: TaskState,
        should_fail: bool,
    }

    impl TestTask {
        fn new(id: String, should_fail: bool) -> Self {
            TestTask {
                id,
                state: TaskState::Ready,
                should_fail,
            }
        }
    }

    impl Task for TestTask {
        fn id(&self) -> &str {
            &self.id
        }

        fn run(&mut self) -> Result<(), String> {
            if self.should_fail {
                Err("Task failed".to_string())
            } else {
                Ok(())
            }
        }

        fn state(&self) -> &TaskState {
            &self.state
        }

        fn set_state(&mut self, state: TaskState) {
            self.state = state;
        }
    }

    #[test]
    fn test_basic_workflow() {
        let mut workflow = Workflow::new("test".to_string());

        workflow.add_task(Box::new(TestTask::new("task1".to_string(), false))).unwrap();
        workflow.add_task(Box::new(TestTask::new("task2".to_string(), false))).unwrap();

        assert!(workflow.run().is_ok());
        assert_eq!(workflow.state(), &WorkflowState::Complete);
    }

    #[test]
    fn test_failing_workflow() {
        let mut workflow = Workflow::new("test".to_string());

        workflow.add_task(Box::new(TestTask::new("task1".to_string(), true))).unwrap();

        assert!(workflow.run().is_err());
        assert!(matches!(workflow.state(), &WorkflowState::Failed(_)));
    }

    #[test]
    fn test_dependency_cycle() {
        let mut workflow = Workflow::new("test".to_string());

        struct CyclicTask {
            id: String,
            state: TaskState,
            deps: Vec<String>,
        }

        impl Task for CyclicTask {
            fn id(&self) -> &str { &self.id }
            fn run(&mut self) -> Result<(), String> { Ok(()) }
            fn state(&self) -> &TaskState { &self.state }
            fn set_state(&mut self, state: TaskState) { self.state = state; }
            fn dependencies(&self) -> &[String] { &self.deps }
        }

        workflow.add_task(Box::new(CyclicTask {
            id: "task1".to_string(),
            state: TaskState::Ready,
            deps: vec!["task2".to_string()],
        })).unwrap();

        assert!(workflow.add_task(Box::new(CyclicTask {
            id: "task2".to_string(),
            state: TaskState::Ready,
            deps: vec!["task1".to_string()],
        })).is_err());
    }
}