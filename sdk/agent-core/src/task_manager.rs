use async_trait::async_trait;

#[derive(Debug)]
pub enum TaskError {
    TaskFailed(String),
    TaskNotFound(String),
}

#[async_trait]
pub trait Task: Send + Sync {
    async fn execute(&self) -> Result<(), TaskError>;
}

pub struct TaskManager {
    tasks: Vec<Box<dyn Task>>,
}

impl TaskManager {
    pub fn new() -> Self {
        Self { tasks: Vec::new() }
    }
    pub fn add_task<T: Task + 'static>(&mut self, task: T) {}
    pub async fn execute_all(&self) {}
}
