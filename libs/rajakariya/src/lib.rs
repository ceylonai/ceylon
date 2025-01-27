use std::collections::{HashMap, HashSet};
use std::error::Error;
use std::fmt;

// Enhanced state management
#[derive(Debug, Clone, PartialEq)]
pub enum TaskState {
    Pending,
    Running,
    Completed,
    Failed,
    Cancelled,
    Blocked,      // New state for dependency management
    Skipped,      // New state for conditional tasks
}

#[derive(Debug, Clone, PartialEq)]
pub enum WorkflowState {
    Created,
    Running,
    Completed,
    Failed,
    Cancelled,
    PartiallyCompleted,  // New state for conditional workflows
}

// Enhanced error types
#[derive(Debug)]
pub enum WorkflowError {
    TaskError(String),
    InvalidState(String),
    DependencyError(String),
    ValidationError(String),
    ConditionError(String),
}

impl fmt::Display for WorkflowError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            WorkflowError::TaskError(msg) => write!(f, "Task error: {}", msg),
            WorkflowError::InvalidState(msg) => write!(f, "Invalid state: {}", msg),
            WorkflowError::DependencyError(msg) => write!(f, "Dependency error: {}", msg),
            WorkflowError::ValidationError(msg) => write!(f, "Validation error: {}", msg),
            WorkflowError::ConditionError(msg) => write!(f, "Condition error: {}", msg),
        }
    }
}

impl Error for WorkflowError {}

// Enhanced Task trait with validation and conditions
pub trait Task {
    fn execute(&mut self) -> Result<(), WorkflowError>;
    fn validate(&self) -> Result<(), WorkflowError> {
        Ok(()) // Default implementation
    }
    fn get_state(&self) -> &TaskState;
    fn set_state(&mut self, state: TaskState);
    fn get_id(&self) -> &str;
    fn get_dependencies(&self) -> Vec<String> {
        Vec::new() // Default: no dependencies
    }
    fn should_execute(&self) -> bool {
        true // Default: always execute
    }
}

// Data processing task
#[derive(Debug)]
pub struct DataProcessingTask {
    id: String,
    state: TaskState,
    data: Vec<i32>,
    threshold: i32,
}

impl DataProcessingTask {
    pub fn new(id: String, data: Vec<i32>, threshold: i32) -> Self {
        DataProcessingTask {
            id,
            state: TaskState::Pending,
            data,
            threshold,
        }
    }
}

impl Task for DataProcessingTask {
    fn execute(&mut self) -> Result<(), WorkflowError> {
        println!("Processing data for task: {}", self.id);

        let sum: i32 = self.data.iter().sum();
        if sum > self.threshold {
            println!("Data sum {} exceeds threshold {}", sum, self.threshold);
            Ok(())
        } else {
            Err(WorkflowError::TaskError(format!(
                "Data sum {} below threshold {}", sum, self.threshold
            )))
        }
    }

    fn validate(&self) -> Result<(), WorkflowError> {
        if self.data.is_empty() {
            return Err(WorkflowError::ValidationError("Empty data set".to_string()));
        }
        Ok(())
    }

    fn get_state(&self) -> &TaskState {
        &self.state
    }

    fn set_state(&mut self, state: TaskState) {
        self.state = state;
    }

    fn get_id(&self) -> &str {
        &self.id
    }
}

// Conditional task
#[derive()]
pub struct ConditionalTask {
    id: String,
    state: TaskState,
    condition: Box<dyn Fn() -> bool>,
    dependencies: Vec<String>,
}

impl ConditionalTask {
    pub fn new(id: String, condition: Box<dyn Fn() -> bool>, dependencies: Vec<String>) -> Self {
        ConditionalTask {
            id,
            state: TaskState::Pending,
            condition,
            dependencies,
        }
    }
}

impl Task for ConditionalTask {
    fn execute(&mut self) -> Result<(), WorkflowError> {
        println!("Executing conditional task: {}", self.id);
        Ok(())
    }

    fn should_execute(&self) -> bool {
        (self.condition)()
    }

    fn get_state(&self) -> &TaskState {
        &self.state
    }

    fn set_state(&mut self, state: TaskState) {
        self.state = state;
    }

    fn get_id(&self) -> &str {
        &self.id
    }

    fn get_dependencies(&self) -> Vec<String> {
        self.dependencies.clone()
    }
}

// Enhanced workflow with dependency management
#[derive()]
pub struct Workflow {
    id: String,
    name: String,
    state: WorkflowState,
    tasks: Vec<Box<dyn Task>>,
    completed_tasks: HashSet<String>,
}

impl Workflow {
    pub fn new(id: String, name: String) -> Self {
        Workflow {
            id,
            name,
            state: WorkflowState::Created,
            tasks: Vec::new(),
            completed_tasks: HashSet::new(),
        }
    }

    pub fn add_task(&mut self, task: Box<dyn Task>) {
        self.tasks.push(task);
    }

    pub fn validate(&self) -> Result<(), WorkflowError> {
        // Validate individual tasks
        for task in &self.tasks {
            task.validate()?;
        }

        // Check for circular dependencies
        let mut task_map: HashMap<&str, Vec<String>> = HashMap::new();
        for task in &self.tasks {
            task_map.insert(task.get_id(), task.get_dependencies());
        }

        for task in &self.tasks {
            let mut visited = HashSet::new();
            let mut stack = Vec::new();
            if self.has_circular_dependencies(task.get_id(), &task_map, &mut visited, &mut stack) {
                return Err(WorkflowError::DependencyError(
                    format!("Circular dependency detected for task {}", task.get_id())
                ));
            }
        }

        Ok(())
    }

    fn has_circular_dependencies(
        &self,
        task_id: &str,
        task_map: &HashMap<&str, Vec<String>>,
        visited: &mut HashSet<String>,
        stack: &mut Vec<String>
    ) -> bool {
        if stack.contains(&task_id.to_string()) {
            return true;
        }
        if visited.contains(&task_id.to_string()) {
            return false;
        }

        visited.insert(task_id.to_string());
        stack.push(task_id.to_string());

        if let Some(dependencies) = task_map.get(task_id) {
            for dep in dependencies {
                if self.has_circular_dependencies(dep, task_map, visited, stack) {
                    return true;
                }
            }
        }

        stack.pop();
        false
    }

    pub fn execute(&mut self) -> Result<(), WorkflowError> {
        self.validate()?;
        self.state = WorkflowState::Running;

        // Track if any tasks were skipped
        let mut any_skipped = false;

        for task in &mut self.tasks {
            // Check dependencies
            let deps = task.get_dependencies();
            let deps_met = deps.iter().all(|dep| self.completed_tasks.contains(dep));

            if !deps_met {
                task.set_state(TaskState::Blocked);
                self.state = WorkflowState::Failed;
                return Err(WorkflowError::DependencyError(
                    format!("Unmet dependencies for task {}", task.get_id())
                ));
            }

            // Check if task should execute
            if !task.should_execute() {
                task.set_state(TaskState::Skipped);
                any_skipped = true;
                continue;
            }

            task.set_state(TaskState::Running);

            match task.execute() {
                Ok(_) => {
                    task.set_state(TaskState::Completed);
                    self.completed_tasks.insert(task.get_id().to_string());
                }
                Err(e) => {
                    task.set_state(TaskState::Failed);
                    self.state = WorkflowState::Failed;
                    return Err(e);
                }
            }
        }

        self.state = if any_skipped {
            WorkflowState::PartiallyCompleted
        } else {
            WorkflowState::Completed
        };

        Ok(())
    }
}

// Example usage
