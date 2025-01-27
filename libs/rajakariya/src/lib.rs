use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use uuid::Uuid;

// Core state enums
#[derive(Debug, Clone, PartialEq)]
pub enum TaskState {
    Pending,
    Running,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, PartialEq)]
pub enum WorkflowState {
    Created,
    Running,
    Completed,
    Failed,
    Cancelled,
}

// Error handling
#[derive(Debug)]
pub enum WorkflowError {
    TaskError(String),
    InvalidState(String),
    NotFound(String),
}

impl fmt::Display for WorkflowError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            WorkflowError::TaskError(msg) => write!(f, "Task error: {}", msg),
            WorkflowError::InvalidState(msg) => write!(f, "Invalid state: {}", msg),
            WorkflowError::NotFound(msg) => write!(f, "Not found: {}", msg),
        }
    }
}

impl Error for WorkflowError {}

// Task trait
pub trait Task {
    fn execute(&mut self) -> Result<(), WorkflowError>;
    fn get_state(&self) -> &TaskState;
    fn set_state(&mut self, state: TaskState);
}

// Workflow structure
#[derive()]
pub struct Workflow {
    id: Uuid,
    name: String,
    state: WorkflowState,
    tasks: Vec<Box<dyn Task>>,
}

impl Workflow {
    pub fn new(name: String) -> Self {
        Workflow {
            id: Uuid::new_v4(),
            name,
            state: WorkflowState::Created,
            tasks: Vec::new(),
        }
    }

    pub fn add_task(&mut self, task: Box<dyn Task>) {
        self.tasks.push(task);
    }

    pub fn get_state(&self) -> &WorkflowState {
        &self.state
    }

    pub fn get_id(&self) -> &Uuid {
        &self.id
    }

    pub fn execute(&mut self) -> Result<(), WorkflowError> {
        self.state = WorkflowState::Running;

        for task in &mut self.tasks {
            task.set_state(TaskState::Running);

            match task.execute() {
                Ok(_) => {
                    task.set_state(TaskState::Completed);
                }
                Err(e) => {
                    task.set_state(TaskState::Failed);
                    self.state = WorkflowState::Failed;
                    return Err(e);
                }
            }
        }

        self.state = WorkflowState::Completed;
        Ok(())
    }
}

// Workflow Engine
pub struct WorkflowEngine {
    workflows: HashMap<Uuid, Workflow>,
}

impl WorkflowEngine {
    pub fn new() -> Self {
        WorkflowEngine {
            workflows: HashMap::new(),
        }
    }

    pub fn create_workflow(&mut self, name: String) -> Uuid {
        let workflow = Workflow::new(name);
        let id = workflow.get_id().clone();
        self.workflows.insert(id, workflow);
        id
    }

    pub fn get_workflow(&self, id: &Uuid) -> Option<&Workflow> {
        self.workflows.get(id)
    }

    pub fn get_workflow_mut(&mut self, id: &Uuid) -> Option<&mut Workflow> {
        self.workflows.get_mut(id)
    }

    pub fn execute_workflow(&mut self, id: &Uuid) -> Result<(), WorkflowError> {
        if let Some(workflow) = self.workflows.get_mut(id) {
            workflow.execute()
        } else {
            Err(WorkflowError::NotFound("Workflow not found".to_string()))
        }
    }
}

// Example task implementation
#[derive(Debug)]
pub struct SimpleTask {
    name: String,
    state: TaskState,
}

impl SimpleTask {
    pub fn new(name: String) -> Self {
        SimpleTask {
            name,
            state: TaskState::Pending,
        }
    }
}

impl Task for SimpleTask {
    fn execute(&mut self) -> Result<(), WorkflowError> {
        println!("Executing task: {}", self.name);
        // Add task logic here
        Ok(())
    }

    fn get_state(&self) -> &TaskState {
        &self.state
    }

    fn set_state(&mut self, state: TaskState) {
        self.state = state;
    }
}

// Example usage
